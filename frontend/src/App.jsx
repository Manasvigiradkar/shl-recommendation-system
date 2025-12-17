import React, { useState } from 'react';
import { Search, Link, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export default function SHLRecommendationSystem() {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [apiUrl, setApiUrl] = useState('http://localhost:8000');

  const sampleQueries = [
    "I am hiring for Java developers who can also collaborate effectively with my business teams.",
    "Looking to hire mid-level professionals who are proficient in Python, SQL and JavaScript.",
    "Need candidates with strong cognitive abilities and good personality fit for analyst role."
  ];

  const handleSearch = async () => {
    if (!query.trim()) {
      setError('Please enter a query');
      return;
    }

    setLoading(true);
    setError('');
    setResults([]);

    try {
      const response = await fetch(`${apiUrl}/recommend`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ query: query.trim() }),
      });

      if (!response.ok) {
        throw new Error(`API Error: ${response.status}`);
      }

      const data = await response.json();
      
      if (data.recommendations && data.recommendations.length > 0) {
        setResults(data.recommendations);
      } else {
        setError('No recommendations found');
      }
    } catch (err) {
      setError(`Failed to fetch recommendations: ${err.message}`);
      console.error('Error:', err);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSearch();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 via-white to-purple-50">
      <div className="max-w-7xl mx-auto px-4 py-8">
        {/* Header */}
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-gray-900 mb-2">
            SHL Assessment Recommendation System
          </h1>
          <p className="text-gray-600">
            Find the perfect assessments for your hiring needs using AI
          </p>
        </div>

        {/* API Configuration */}
        <div className="bg-white rounded-lg shadow-sm p-4 mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            API Endpoint
          </label>
          <input
            type="text"
            value={apiUrl}
            onChange={(e) => setApiUrl(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            placeholder="http://localhost:8000"
          />
        </div>

        {/* Search Box */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="mb-4">
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Enter Job Description or Query
            </label>
            <textarea
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"
              rows="4"
              placeholder="E.g., I am hiring for Java developers who can also collaborate effectively with my business teams..."
            />
          </div>

          <button
            onClick={handleSearch}
            disabled={loading}
            className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg font-medium hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="animate-spin" size={20} />
                Searching...
              </>
            ) : (
              <>
                <Search size={20} />
                Get Recommendations
              </>
            )}
          </button>

          {/* Sample Queries */}
          <div className="mt-4">
            <p className="text-sm font-medium text-gray-700 mb-2">Try these examples:</p>
            <div className="space-y-2">
              {sampleQueries.map((sample, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(sample)}
                  className="text-left w-full text-sm text-blue-600 hover:text-blue-800 hover:bg-blue-50 p-2 rounded transition-colors"
                >
                  {sample}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 mb-6 flex items-start gap-3">
            <AlertCircle className="text-red-500 flex-shrink-0 mt-0.5" size={20} />
            <div>
              <p className="text-red-800 font-medium">Error</p>
              <p className="text-red-700 text-sm">{error}</p>
            </div>
          </div>
        )}

        {/* Success Message */}
        {results.length > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6 flex items-center gap-3">
            <CheckCircle2 className="text-green-500 flex-shrink-0" size={20} />
            <p className="text-green-800">
              Found <strong>{results.length}</strong> relevant assessments
            </p>
          </div>
        )}

        {/* Results Table */}
        {results.length > 0 && (
          <div className="bg-white rounded-lg shadow-lg overflow-hidden">
            <div className="px-6 py-4 bg-gray-50 border-b">
              <h2 className="text-xl font-semibold text-gray-900">
                Recommended Assessments
              </h2>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 border-b">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Rank
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Assessment Name
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Score
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                      Link
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {results.map((result, idx) => (
                    <tr key={idx} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center justify-center w-8 h-8 bg-blue-100 text-blue-800 rounded-full font-semibold">
                          {idx + 1}
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-sm font-medium text-gray-900">
                          {result.assessment_name}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="px-3 py-1 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          {result.score ? result.score.toFixed(3) : 'N/A'}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <a
                          href={result.url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 text-blue-600 hover:text-blue-800 transition-colors"
                        >
                          <Link size={16} />
                          <span className="text-sm">View Details</span>
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Footer */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>Built with React + FastAPI + Google Gemini</p>
        </div>
      </div>
    </div>
  );
}