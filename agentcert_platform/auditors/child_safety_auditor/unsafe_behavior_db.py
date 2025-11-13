"""
Unsafe Behavior Database - Vector database for RAG-based unsafe behavior retrieval
"""

import json
import os
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

# Try to import ChromaDB
try:
    import chromadb
    from chromadb.config import Settings
    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    logger.warning("ChromaDB not installed. RAG functionality will be limited.")


class UnsafeBehaviorDatabase:
    """Vector database for unsafe behavior examples using RAG"""
    
    def __init__(self, dataset_dir: str, openai_api_key: Optional[str] = None):
        """
        Initialize the unsafe behavior database.
        
        Args:
            dataset_dir: Directory containing JSON dataset files
            openai_api_key: OpenAI API key for embeddings (optional, uses ChromaDB default if not provided)
        """
        self.dataset_dir = Path(dataset_dir)
        self.openai_api_key = openai_api_key
        
        if not HAS_CHROMADB:
            logger.error("ChromaDB not available. Install with: pip install chromadb")
            self.client = None
            self.collection = None
            return
        
        # Initialize ChromaDB (persistent storage)
        db_path = Path(__file__).parent / "data" / "chroma_db"
        db_path.mkdir(parents=True, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(
                path=str(db_path),
                settings=Settings(anonymized_telemetry=False)
            )
            
            # Get or create collection
            self.collection = self.client.get_or_create_collection(
                name="unsafe_behaviors",
                metadata={"description": "Unsafe behavior examples for child safety auditing"}
            )
            
            # Load and index dataset if not already indexed
            # Note: We'll load it lazily on first use to avoid blocking initialization
            if self.collection.count() == 0:
                logger.info("Database is empty, will load and index datasets on first use...")
            else:
                logger.info(f"Database already contains {self.collection.count()} entries")
        except Exception as e:
            logger.error(f"Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None
    
    async def _load_and_index_dataset(self):
        """Load JSON dataset files and create embeddings"""
        if not self.dataset_dir.exists():
            logger.warning(f"Dataset directory not found at {self.dataset_dir}")
            return
        
        if not self.collection:
            logger.error("ChromaDB collection not available")
            return
        
        # Find all JSON files (excluding safe.json for now, or include it as negative examples)
        json_files = list(self.dataset_dir.glob("*.json"))
        
        all_behaviors = []
        
        for json_file in json_files:
            if json_file.name == "safe.json":
                # Skip safe examples for now, or use them as negative examples
                continue
            
            logger.info(f"Loading {json_file.name}...")
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if isinstance(data, list):
                    behaviors = data
                else:
                    behaviors = [data]
                
                # Add file source to each behavior
                for behavior in behaviors:
                    behavior['_source_file'] = json_file.name
                
                all_behaviors.extend(behaviors)
                logger.info(f"Loaded {len(behaviors)} behaviors from {json_file.name}")
            except Exception as e:
                logger.error(f"Error loading {json_file.name}: {e}")
                continue
        
        if not all_behaviors:
            logger.warning("No behaviors loaded from dataset files")
            return
        
        logger.info(f"Total behaviors to index: {len(all_behaviors)}")
        
        # Prepare data for indexing
        texts = []
        metadatas = []
        ids = []
        
        for idx, behavior in enumerate(all_behaviors):
            # Create searchable text (content + explanation + context)
            content = behavior.get('content', '')
            explanation = behavior.get('explanation', '')
            context = behavior.get('context', '')
            
            searchable_text = f"{content} {explanation} {context}".strip()
            
            if not searchable_text:
                continue
            
            texts.append(searchable_text)
            
            # Store metadata
            user_age = behavior.get('user_age')
            if isinstance(user_age, str):
                try:
                    user_age = int(user_age)
                except:
                    user_age = 10  # Default
            
            metadatas.append({
                "category": behavior.get("category", "unknown"),
                "violation_type": behavior.get("violation_type", "unknown"),
                "severity": behavior.get("severity", "medium"),
                "user_age": user_age or 10,
                "content": content,
                "explanation": explanation,
                "context": context,
                "source_file": behavior.get("_source_file", "unknown"),
            })
            ids.append(f"behavior_{idx}")
        
        # Add to ChromaDB in batches (ChromaDB handles embeddings automatically)
        batch_size = 100
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i+batch_size]
            batch_metadatas = metadatas[i:i+batch_size]
            batch_ids = ids[i:i+batch_size]
            
            try:
                self.collection.add(
                    documents=batch_texts,
                    metadatas=batch_metadatas,
                    ids=batch_ids
                )
                logger.info(f"Indexed batch {i//batch_size + 1}/{(len(texts)-1)//batch_size + 1}")
            except Exception as e:
                logger.error(f"Error indexing batch {i//batch_size + 1}: {e}")
        
        logger.info(f"Successfully indexed {len(texts)} unsafe behavior examples")
    
    async def retrieve_similar_behaviors(
        self,
        query: str,
        category: Optional[str] = None,
        age_range: Tuple[int, int] = (8, 13),
        top_k: int = 5,
        min_severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve similar unsafe behaviors using semantic search
        
        Args:
            query: Search query (e.g., category description or test context)
            category: Filter by category (optional)
            age_range: Filter by age range (min, max)
            top_k: Number of results to return
            min_severity: Minimum severity level (critical > high > medium > low)
        
        Returns:
            List of similar unsafe behaviors with metadata
        """
        if not self.collection:
            logger.warning("ChromaDB collection not available")
            return []
        
        # Lazy load dataset if empty
        if self.collection.count() == 0:
            logger.info("Database is empty, loading and indexing datasets...")
            try:
                await self._load_and_index_dataset()
            except Exception as e:
                logger.error(f"Error loading dataset: {e}")
                return []
        
        # Build query with category context
        search_query = query
        if category:
            search_query = f"{category}: {query}"
        
        # Build where clause for filtering
        where_clause = {}
        if category:
            # Map auditor categories to dataset categories
            dataset_category = self._map_auditor_to_dataset_category(category)
            if dataset_category:
                where_clause["category"] = dataset_category
        
        try:
            # Query ChromaDB
            results = self.collection.query(
                query_texts=[search_query],
                n_results=top_k * 3,  # Get more to filter by age and severity
                where=where_clause if where_clause else None
            )
            
            # Process and filter results
            similar_behaviors = []
            if results["documents"] and len(results["documents"][0]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = results["metadatas"][0][i]
                    distance = results["distances"][0][i] if "distances" in results and results["distances"] else 0
                    
                    # Filter by age range
                    user_age = metadata.get("user_age", 10)
                    if isinstance(user_age, str):
                        try:
                            user_age = int(user_age)
                        except:
                            user_age = 10
                    
                    if not (age_range[0] <= user_age <= age_range[1]):
                        continue
                    
                    # Filter by severity if specified
                    severity = metadata.get("severity", "medium")
                    if min_severity and not self._severity_gte(severity, min_severity):
                        continue
                    
                    similar_behaviors.append({
                        "content": metadata.get("content", doc),
                        "category": metadata.get("category"),
                        "violation_type": metadata.get("violation_type"),
                        "severity": severity,
                        "explanation": metadata.get("explanation"),
                        "context": metadata.get("context"),
                        "user_age": user_age,
                        "similarity_score": 1 - distance if distance else 1.0
                    })
                    
                    if len(similar_behaviors) >= top_k:
                        break
            
            return similar_behaviors
        
        except Exception as e:
            logger.error(f"Error retrieving similar behaviors: {e}")
            return []
    
    def _map_auditor_to_dataset_category(self, auditor_category: str) -> Optional[str]:
        """Map auditor categories to dataset categories"""
        mapping = {
            "age_appropriate_content": "nsfw_content",
            "personal_information_protection": "privacy_violation",
            "social_engineering_resistance": "grooming",  # Grooming often involves social engineering
            "inappropriate_content_filtering": "nsfw_content",
            "boundary_respect": "self_harm",  # Self-harm is a boundary violation
            "grooming_pattern_detection": "grooming",
            "sneaky_prompts": "nsfw_content",  # Sneaky prompts often try to get NSFW content
            "authority_impersonation": "grooming",  # Authority manipulation is a grooming tactic
            "peer_pressure": "grooming",  # Peer pressure is often used in grooming
            "emotional_manipulation": "grooming",  # Emotional manipulation is a grooming technique
            "role_playing_bypass": "nsfw_content",  # Role-playing often attempts to get inappropriate content
            "gradual_escalation": "nsfw_content",  # Gradual escalation often leads to inappropriate content
            "technical_bypass": "nsfw_content",  # Technical bypass attempts often target inappropriate content
        }
        return mapping.get(auditor_category)
    
    def _severity_gte(self, severity1: str, severity2: str) -> bool:
        """Check if severity1 >= severity2"""
        severity_order = {"low": 1, "medium": 2, "high": 3, "critical": 4}
        return severity_order.get(severity1.lower(), 0) >= severity_order.get(severity2.lower(), 0)


# Singleton instance
_behavior_db = None


def get_behavior_database(dataset_dir: Optional[str] = None, openai_api_key: Optional[str] = None) -> Optional[UnsafeBehaviorDatabase]:
    """Get or create the unsafe behavior database singleton"""
    global _behavior_db
    
    if _behavior_db is None:
        if dataset_dir is None:
            # Default to child_safety_data directory (one level up from agentcert-platform)
            base_path = Path(__file__).parent.parent.parent.parent.parent
            dataset_dir = base_path / "child_safety_data"
        
        _behavior_db = UnsafeBehaviorDatabase(str(dataset_dir), openai_api_key)
    
    return _behavior_db

