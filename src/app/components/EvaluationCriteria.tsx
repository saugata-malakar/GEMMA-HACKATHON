import { Lightbulb, Video, Code2 } from 'lucide-react';

const criteria = [
  {
    name: 'Impact & Vision',
    points: 40,
    icon: Lightbulb,
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    borderColor: 'border-yellow-200',
    description: 'How clearly does your project address a significant real-world problem? Is the vision inspiring with tangible potential for positive change?'
  },
  {
    name: 'Video Pitch & Storytelling',
    points: 30,
    icon: Video,
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    borderColor: 'border-purple-200',
    description: 'How exciting and engaging is your video? Does it tell a powerful story that captures imagination?'
  },
  {
    name: 'Technical Depth & Execution',
    points: 30,
    icon: Code2,
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    borderColor: 'border-blue-200',
    description: 'How innovative is your use of Gemma 4? Is the technology real, functional, and well-engineered?'
  }
];

export function EvaluationCriteria() {
  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-2xl mb-4">Evaluation Criteria</h2>

      <div className="space-y-4">
        {criteria.map((criterion) => {
          const Icon = criterion.icon;
          const percentage = (criterion.points / 100) * 100;

          return (
            <div key={criterion.name} className={`border ${criterion.borderColor} ${criterion.bgColor} rounded-lg p-4`}>
              <div className="flex items-start gap-4 mb-3">
                <div className="flex-shrink-0">
                  <Icon className={`w-6 h-6 ${criterion.color}`} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-2">
                    <h3 className="font-semibold text-gray-900">{criterion.name}</h3>
                    <span className={`text-2xl font-bold ${criterion.color}`}>{criterion.points}</span>
                  </div>
                  <p className="text-sm text-gray-700 mb-3">{criterion.description}</p>

                  {/* Progress bar showing points */}
                  <div className="w-full bg-white rounded-full h-2 border border-gray-200">
                    <div
                      className={`h-2 rounded-full ${criterion.color.replace('text-', 'bg-')}`}
                      style={{ width: `${percentage}%` }}
                    />
                  </div>
                </div>
              </div>
            </div>
          );
        })}

        <div className="mt-6 p-4 bg-gray-50 rounded-lg border border-gray-200">
          <div className="text-sm text-gray-700">
            <span className="font-semibold">Total: 100 points</span>
            <div className="mt-2 text-xs text-gray-600">
              Your project will be judged primarily on your video demo, with the writeup and code repository used to verify functionality.
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
