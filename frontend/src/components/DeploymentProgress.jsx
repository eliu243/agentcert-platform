import { useState, useEffect } from 'react';

const DeploymentProgress = ({ isDeploying, deploymentMode = 'local' }) => {
  const [currentStep, setCurrentStep] = useState(0);
  const [stepProgress, setStepProgress] = useState(0);

  // Define deployment steps based on mode
  const steps = deploymentMode === 'ec2' 
    ? [
        { label: 'Cloning repository', description: 'Downloading agent code from GitHub' },
        { label: 'Validating agent', description: 'Checking agent structure and dependencies' },
        { label: 'Creating cloud instance', description: 'Provisioning EC2 instance' },
        { label: 'Setting up infrastructure', description: 'Configuring security groups and networking' },
        { label: 'Installing dependencies', description: 'Installing NEST and required packages' },
        { label: 'Deploying agent', description: 'Starting agent on cloud instance' },
        { label: 'Registering agent', description: 'Registering with NEST registry' },
        { label: 'Health check', description: 'Verifying agent is running correctly' },
      ]
    : [
        { label: 'Cloning repository', description: 'Downloading agent code from GitHub' },
        { label: 'Validating agent', description: 'Checking agent structure and dependencies' },
        { label: 'Setting up environment', description: 'Configuring API keys and environment variables' },
        { label: 'Starting agent', description: 'Launching agent process' },
        { label: 'Health check', description: 'Verifying agent is running correctly' },
      ];

  useEffect(() => {
    if (!isDeploying) {
      // Reset when deployment stops
      setCurrentStep(0);
      setStepProgress(0);
      return;
    }

    // Simulate progress through steps
    // This is an approximation since we don't have real-time updates
    const totalSteps = steps.length;
    const stepDuration = deploymentMode === 'ec2' ? 10000 : 4000; // EC2 takes longer (milliseconds per step)
    const updateInterval = 50; // Update every 50ms for smooth animation
    const progressPerUpdate = (100 / stepDuration) * updateInterval; // Calculate progress increment per update

    let step = 0;
    let progress = 0;
    const interval = setInterval(() => {
      progress += progressPerUpdate;
      
      // Move to next step when progress reaches 100%
      if (progress >= 100 && step < totalSteps - 1) {
        step += 1;
        progress = 0;
      } else if (step === totalSteps - 1 && progress >= 95) {
        // Stay on last step at 95% until deployment actually completes
        progress = 95;
      }

      setCurrentStep(step);
      setStepProgress(Math.min(progress, 100));
    }, updateInterval);

    return () => clearInterval(interval);
  }, [isDeploying, deploymentMode, steps.length]);

  if (!isDeploying) {
    return null;
  }

  return (
    <div className="w-full bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-xl p-6 mt-6">
      <div className="mb-4">
        <h3 className="text-lg font-semibold text-white mb-1">
          Deployment Progress
        </h3>
        <p className="text-sm text-gray-400">
          {deploymentMode === 'ec2' 
            ? 'Deploying to cloud infrastructure (this may take 1-2 minutes)'
            : 'Deploying locally (this may take 30-60 seconds)'}
        </p>
      </div>

      <div className="space-y-4">
        {steps.map((step, index) => {
          const isActive = index === currentStep;
          const isComplete = index < currentStep;
          const progress = isActive ? stepProgress : isComplete ? 100 : 0;

          return (
            <div key={index} className="relative">
              {/* Step indicator */}
              <div className="flex items-start gap-4">
                {/* Step number/icon */}
                <div className="flex-shrink-0">
                  {isComplete ? (
                    <div className="w-8 h-8 rounded-full bg-green-500 flex items-center justify-center">
                      <svg className="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  ) : isActive ? (
                    <div className="w-8 h-8 rounded-full bg-cyan-500 flex items-center justify-center animate-pulse">
                      <div className="w-3 h-3 rounded-full bg-white"></div>
                    </div>
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-gray-600 flex items-center justify-center">
                      <span className="text-xs font-semibold text-gray-300">{index + 1}</span>
                    </div>
                  )}
                </div>

                {/* Step content */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <p className={`text-sm font-medium ${
                      isActive ? 'text-cyan-400' : isComplete ? 'text-green-400' : 'text-gray-400'
                    }`}>
                      {step.label}
                    </p>
                    {isActive && (
                      <span className="text-xs text-gray-500">{Math.round(progress)}%</span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mb-2">{step.description}</p>
                  
                  {/* Progress bar */}
                  {isActive && (
                    <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className="h-full bg-gradient-to-r from-cyan-500 to-blue-600 rounded-full transition-all duration-300 ease-out"
                        style={{ width: `${progress}%` }}
                      />
                    </div>
                  )}
                </div>
              </div>

              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className={`absolute left-4 top-10 w-0.5 h-4 ${
                  isComplete ? 'bg-green-500' : 'bg-gray-600'
                }`} />
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default DeploymentProgress;

