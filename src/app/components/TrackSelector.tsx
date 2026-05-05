import { useState } from 'react';
import { Award, HeartPulse, Globe, GraduationCap, Users, Shield, Smartphone, Cpu, HardDrive, Box, Zap } from 'lucide-react';

const tracks = {
  main: {
    name: 'Main Track',
    prize: '$100,000',
    icon: Award,
    description: 'Best overall projects with exceptional vision and impact',
    color: 'from-yellow-400 to-orange-500'
  },
  impact: [
    { name: 'Health & Sciences', prize: '$10,000', icon: HeartPulse, color: 'from-red-400 to-pink-500' },
    { name: 'Global Resilience', prize: '$10,000', icon: Globe, color: 'from-green-400 to-teal-500' },
    { name: 'Future of Education', prize: '$10,000', icon: GraduationCap, color: 'from-blue-400 to-cyan-500' },
    { name: 'Digital Equity & Inclusivity', prize: '$10,000', icon: Users, color: 'from-purple-400 to-pink-500' },
    { name: 'Safety & Trust', prize: '$10,000', icon: Shield, color: 'from-indigo-400 to-purple-500' }
  ],
  technology: [
    { name: 'Cactus', prize: '$10,000', icon: Smartphone, description: 'Local-first mobile/wearable' },
    { name: 'LiteRT', prize: '$10,000', icon: Cpu, description: 'Google AI Edge implementation' },
    { name: 'llama.cpp', prize: '$10,000', icon: HardDrive, description: 'Resource-constrained hardware' },
    { name: 'Ollama', prize: '$10,000', icon: Box, description: 'Running locally via Ollama' },
    { name: 'Unsloth', prize: '$10,000', icon: Zap, description: 'Fine-tuned model' }
  ]
};

export function TrackSelector() {
  const [selectedTrack, setSelectedTrack] = useState<string>('main');
  const [selectedImpact, setSelectedImpact] = useState<string>('');
  const [selectedTech, setSelectedTech] = useState<string>('');

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <h2 className="text-2xl mb-4">Select Your Track</h2>

      <div className="space-y-6">
        {/* Main Track */}
        <div>
          <button
            onClick={() => setSelectedTrack('main')}
            className={`w-full p-4 rounded-lg border-2 transition-all ${
              selectedTrack === 'main'
                ? 'border-yellow-500 bg-yellow-50'
                : 'border-gray-200 hover:border-gray-300'
            }`}
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className={`p-2 rounded-lg bg-gradient-to-br ${tracks.main.color}`}>
                  <Award className="w-6 h-6 text-white" />
                </div>
                <div className="text-left">
                  <div className="font-semibold">{tracks.main.name}</div>
                  <div className="text-sm text-gray-600">{tracks.main.description}</div>
                </div>
              </div>
              <div className="text-lg font-bold text-yellow-600">{tracks.main.prize}</div>
            </div>
          </button>
        </div>

        {/* Impact Track */}
        <div>
          <h3 className="text-lg mb-3">Impact Track ($50,000 total)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {tracks.impact.map((track) => {
              const Icon = track.icon;
              return (
                <button
                  key={track.name}
                  onClick={() => setSelectedImpact(track.name)}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    selectedImpact === track.name
                      ? 'border-purple-500 bg-purple-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg bg-gradient-to-br ${track.color} flex-shrink-0`}>
                      <Icon className="w-5 h-5 text-white" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm">{track.name}</div>
                      <div className="text-sm text-gray-600 mt-1">{track.prize}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>

        {/* Technology Track */}
        <div>
          <h3 className="text-lg mb-3">Special Technology Track ($50,000 total)</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {tracks.technology.map((track) => {
              const Icon = track.icon;
              return (
                <button
                  key={track.name}
                  onClick={() => setSelectedTech(track.name)}
                  className={`p-4 rounded-lg border-2 transition-all text-left ${
                    selectedTech === track.name
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <div className="flex items-start gap-3">
                    <Icon className="w-5 h-5 text-indigo-600 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="font-semibold text-sm">{track.name}</div>
                      <div className="text-xs text-gray-500 mt-1">{track.description}</div>
                      <div className="text-sm text-indigo-600 mt-1">{track.prize}</div>
                    </div>
                  </div>
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
