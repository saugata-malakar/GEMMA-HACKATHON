import { useState } from 'react';
import { Pencil, Save } from 'lucide-react';

export function ProjectOverview() {
  const [isEditing, setIsEditing] = useState(false);
  const [projectData, setProjectData] = useState({
    title: 'My Gemma 4 Project',
    description: 'Enter your project description here...',
    problem: 'What problem does your project solve?',
    solution: 'How does your Gemma 4 application solve it?',
    impact: 'What is the potential real-world impact?'
  });

  const handleSave = () => {
    setIsEditing(false);
    // In a real app, you'd save to localStorage or a backend
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-2xl">Project Overview</h2>
        <button
          onClick={() => isEditing ? handleSave() : setIsEditing(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          {isEditing ? (
            <>
              <Save className="w-4 h-4" />
              Save
            </>
          ) : (
            <>
              <Pencil className="w-4 h-4" />
              Edit
            </>
          )}
        </button>
      </div>

      <div className="space-y-6">
        {/* Project Title */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Project Title
          </label>
          {isEditing ? (
            <input
              type="text"
              value={projectData.title}
              onChange={(e) => setProjectData({ ...projectData, title: e.target.value })}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          ) : (
            <div className="text-xl font-semibold text-gray-900">{projectData.title}</div>
          )}
        </div>

        {/* Description */}
        <div>
          <label className="block text-sm font-semibold text-gray-700 mb-2">
            Description
          </label>
          {isEditing ? (
            <textarea
              value={projectData.description}
              onChange={(e) => setProjectData({ ...projectData, description: e.target.value })}
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
          ) : (
            <div className="text-gray-700">{projectData.description}</div>
          )}
        </div>

        {/* Problem Statement */}
        <div className="bg-red-50 border border-red-200 rounded-lg p-4">
          <label className="block text-sm font-semibold text-red-900 mb-2">
            Problem Statement
          </label>
          {isEditing ? (
            <textarea
              value={projectData.problem}
              onChange={(e) => setProjectData({ ...projectData, problem: e.target.value })}
              rows={2}
              className="w-full px-4 py-2 border border-red-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-red-500 bg-white"
            />
          ) : (
            <div className="text-red-800">{projectData.problem}</div>
          )}
        </div>

        {/* Solution */}
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <label className="block text-sm font-semibold text-blue-900 mb-2">
            Your Solution
          </label>
          {isEditing ? (
            <textarea
              value={projectData.solution}
              onChange={(e) => setProjectData({ ...projectData, solution: e.target.value })}
              rows={2}
              className="w-full px-4 py-2 border border-blue-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
            />
          ) : (
            <div className="text-blue-800">{projectData.solution}</div>
          )}
        </div>

        {/* Impact */}
        <div className="bg-green-50 border border-green-200 rounded-lg p-4">
          <label className="block text-sm font-semibold text-green-900 mb-2">
            Expected Impact
          </label>
          {isEditing ? (
            <textarea
              value={projectData.impact}
              onChange={(e) => setProjectData({ ...projectData, impact: e.target.value })}
              rows={2}
              className="w-full px-4 py-2 border border-green-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 bg-white"
            />
          ) : (
            <div className="text-green-800">{projectData.impact}</div>
          )}
        </div>
      </div>
    </div>
  );
}
