import { DeadlineCountdown } from './components/DeadlineCountdown';
import { ProjectOverview } from './components/ProjectOverview';
import { TrackSelector } from './components/TrackSelector';
import { SubmissionChecklist } from './components/SubmissionChecklist';
import { EvaluationCriteria } from './components/EvaluationCriteria';
import { Trophy } from 'lucide-react';

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="bg-gradient-to-br from-purple-500 to-indigo-600 p-2 rounded-lg">
                <Trophy className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">Gemma 4 Good Hackathon</h1>
                <p className="text-sm text-gray-600">Submission Tracker</p>
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-600">Total Prize Pool</div>
              <div className="text-2xl font-bold text-indigo-600">$200,000</div>
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="space-y-8">
          {/* Deadline Countdown */}
          <DeadlineCountdown />

          {/* Two Column Layout */}
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            {/* Left Column - Main Content */}
            <div className="lg:col-span-2 space-y-8">
              <ProjectOverview />
              <SubmissionChecklist />
            </div>

            {/* Right Column - Sidebar */}
            <div className="space-y-8">
              <TrackSelector />
              <EvaluationCriteria />
            </div>
          </div>

          {/* Tips Section */}
          <div className="bg-gradient-to-br from-indigo-50 to-purple-50 border border-indigo-200 rounded-lg p-6">
            <h3 className="text-lg font-semibold text-gray-900 mb-3">💡 Tips for Success</h3>
            <ul className="space-y-2 text-sm text-gray-700">
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span><strong>Tell a story:</strong> Your video is the most important part. Show the problem and your solution compellingly.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span><strong>Real technology:</strong> The writeup and code prove your demo is backed by functional engineering.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span><strong>Publish weights & benchmarks:</strong> If training a model, make your work reproducible.</span>
              </li>
              <li className="flex items-start gap-2">
                <span className="text-indigo-600 font-bold">•</span>
                <span><strong>Multiple prizes:</strong> You can win both a Main Track Prize and a Special Technology Prize.</span>
              </li>
            </ul>
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="bg-white border-t border-gray-200 mt-16">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
          <div className="text-center text-sm text-gray-600">
            <p>Organized by Google DeepMind · 11,936 Entrants · 205 Participants</p>
            <p className="mt-2">Start Date: April 2, 2026 · Final Deadline: May 18, 2026</p>
          </div>
        </div>
      </footer>
    </div>
  );
}