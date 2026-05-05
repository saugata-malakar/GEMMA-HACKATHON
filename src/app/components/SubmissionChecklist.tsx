import { useState } from 'react';
import { CheckCircle2, Circle, FileText, Video, Code, Globe, Image, AlertCircle } from 'lucide-react';

interface ChecklistItem {
  id: string;
  title: string;
  description: string;
  icon: any;
  maxLength?: string;
  required: boolean;
}

const checklistItems: ChecklistItem[] = [
  {
    id: 'writeup',
    title: 'Kaggle Writeup',
    description: 'Technical report (max 1,500 words) explaining architecture and Gemma 4 usage',
    icon: FileText,
    maxLength: '1,500 words max',
    required: true
  },
  {
    id: 'video',
    title: 'Video Demo',
    description: '3-minute YouTube video demonstrating your project in action',
    icon: Video,
    maxLength: '3 minutes max',
    required: true
  },
  {
    id: 'code',
    title: 'Public Code Repository',
    description: 'GitHub or Kaggle Notebook with well-documented implementation',
    icon: Code,
    required: true
  },
  {
    id: 'demo',
    title: 'Live Demo',
    description: 'Working demo URL or files for judges to experience firsthand',
    icon: Globe,
    required: true
  },
  {
    id: 'media',
    title: 'Media Gallery',
    description: 'Cover image (required) and any additional images/videos',
    icon: Image,
    required: true
  }
];

export function SubmissionChecklist() {
  const [completed, setCompleted] = useState<Set<string>>(new Set());
  const [notes, setNotes] = useState<Record<string, string>>({});

  const toggleItem = (id: string) => {
    const newCompleted = new Set(completed);
    if (newCompleted.has(id)) {
      newCompleted.delete(id);
    } else {
      newCompleted.add(id);
    }
    setCompleted(newCompleted);
  };

  const progress = (completed.size / checklistItems.length) * 100;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="mb-6">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-2xl">Submission Requirements</h2>
          <span className="text-sm font-semibold text-indigo-600">
            {completed.size} of {checklistItems.length} complete
          </span>
        </div>

        {/* Progress Bar */}
        <div className="w-full bg-gray-200 rounded-full h-2">
          <div
            className="bg-gradient-to-r from-indigo-500 to-purple-600 h-2 rounded-full transition-all duration-300"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {progress < 100 && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6 flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
          <div className="text-sm text-amber-800">
            All requirements must be completed before the May 19, 2026 deadline. Draft writeups will not be considered.
          </div>
        </div>
      )}

      <div className="space-y-4">
        {checklistItems.map((item) => {
          const Icon = item.icon;
          const isCompleted = completed.has(item.id);

          return (
            <div key={item.id} className="border border-gray-200 rounded-lg p-4 hover:border-gray-300 transition-colors">
              <div className="flex items-start gap-4">
                <button
                  onClick={() => toggleItem(item.id)}
                  className="flex-shrink-0 mt-1"
                >
                  {isCompleted ? (
                    <CheckCircle2 className="w-6 h-6 text-green-600" />
                  ) : (
                    <Circle className="w-6 h-6 text-gray-300" />
                  )}
                </button>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <Icon className="w-5 h-5 text-indigo-600" />
                    <h3 className={`font-semibold ${isCompleted ? 'text-gray-400 line-through' : ''}`}>
                      {item.title}
                    </h3>
                    {item.required && (
                      <span className="text-xs bg-red-100 text-red-700 px-2 py-0.5 rounded">Required</span>
                    )}
                    {item.maxLength && (
                      <span className="text-xs bg-blue-100 text-blue-700 px-2 py-0.5 rounded">
                        {item.maxLength}
                      </span>
                    )}
                  </div>

                  <p className="text-sm text-gray-600 mb-3">{item.description}</p>

                  <input
                    type="text"
                    placeholder="Add URL or notes..."
                    value={notes[item.id] || ''}
                    onChange={(e) => setNotes({ ...notes, [item.id]: e.target.value })}
                    className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-indigo-500"
                  />
                </div>
              </div>
            </div>
          );
        })}
      </div>

      {progress === 100 && (
        <div className="mt-6 bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <div className="text-green-800 font-semibold mb-1">Ready to Submit! 🎉</div>
          <div className="text-sm text-green-700">
            All requirements completed. Don't forget to submit before the deadline!
          </div>
        </div>
      )}
    </div>
  );
}
