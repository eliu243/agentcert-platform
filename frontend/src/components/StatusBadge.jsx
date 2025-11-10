const StatusBadge = ({ status, className = '' }) => {
  const getStatusColor = (status) => {
    const statusLower = status?.toLowerCase() || '';
    
    if (statusLower === 'deployed' || statusLower === 'completed' || statusLower === 'passed' || statusLower === 'excellent') {
      return 'bg-green-100 dark:bg-green-900/30 text-green-800 dark:text-green-200 border-green-200 dark:border-green-700';
    } else if (statusLower === 'running' || statusLower === 'pending') {
      return 'bg-blue-100 dark:bg-blue-900/30 text-blue-800 dark:text-blue-200 border-blue-200 dark:border-blue-700';
    } else if (statusLower === 'failed' || statusLower === 'error' || statusLower === 'poor') {
      return 'bg-red-100 dark:bg-red-900/30 text-red-800 dark:text-red-200 border-red-200 dark:border-red-700';
    } else if (statusLower === 'critical') {
      return 'bg-red-200 dark:bg-red-900/40 text-red-900 dark:text-red-100 border-red-300 dark:border-red-800';
    } else if (statusLower === 'high') {
      return 'bg-orange-100 dark:bg-orange-900/30 text-orange-800 dark:text-orange-200 border-orange-200 dark:border-orange-700';
    } else if (statusLower === 'medium' || statusLower === 'moderate') {
      return 'bg-yellow-100 dark:bg-yellow-900/30 text-yellow-800 dark:text-yellow-200 border-yellow-200 dark:border-yellow-700';
    } else {
      return 'bg-gray-100 dark:bg-gray-700 text-gray-800 dark:text-gray-200 border-gray-200 dark:border-gray-600';
    }
  };

  return (
    <span
      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${getStatusColor(
        status
      )} ${className}`}
    >
      {status}
    </span>
  );
};

export default StatusBadge;

