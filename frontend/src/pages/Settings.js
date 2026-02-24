import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { preferencesAPI } from '../services/api';
import { useAuth } from '../services/AuthContext';
import toast from 'react-hot-toast';
import { Navigate } from 'react-router-dom';

const Settings = () => {
  const { isAuthenticated } = useAuth();
  const queryClient = useQueryClient();
  const [activeTab, setActiveTab] = useState('preferences');

  const { data: preferences, isLoading } = useQuery(
    'preferences',
    () => preferencesAPI.getPreferences().then(res => res.data),
    {
      enabled: isAuthenticated,
    }
  );

  const updatePreferencesMutation = useMutation(
    (data) => preferencesAPI.updatePreferences(data),
    {
      onSuccess: () => {
        queryClient.invalidateQueries('preferences');
        toast.success('Preferences updated successfully!');
      },
      onError: (error) => {
        toast.error(error.response?.data?.detail || 'Failed to update preferences');
      },
    }
  );

  const [formData, setFormData] = useState({
    max_price: '',
    min_price: '',
    max_mileage: '',
    min_year: '',
    max_year: '',
    preferred_makes: [],
    preferred_fuel_types: [],
    max_distance_km: '',
    email_notifications: true,
    notification_frequency: 'instant',
  });

  React.useEffect(() => {
    if (preferences) {
      setFormData({
        max_price: preferences.max_price || '',
        min_price: preferences.min_price || '',
        max_mileage: preferences.max_mileage || '',
        min_year: preferences.min_year || '',
        max_year: preferences.max_year || '',
        preferred_makes: preferences.preferred_makes || [],
        preferred_fuel_types: preferences.preferred_fuel_types || [],
        max_distance_km: preferences.max_distance_km || '',
        email_notifications: preferences.email_notifications ?? true,
        notification_frequency: preferences.notification_frequency || 'instant',
      });
    }
  }, [preferences]);

  if (!isAuthenticated) {
    return <Navigate to="/login" />;
  }

  const handleSubmit = (e) => {
    e.preventDefault();
    updatePreferencesMutation.mutate(formData);
  };

  const handleInputChange = (key, value) => {
    setFormData(prev => ({ ...prev, [key]: value }));
  };

  const carMakes = [
    'Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Opel', 'Ford',
    'Renault', 'Peugeot', 'Citroën', 'Toyota', 'Nissan', 'Honda',
    'Mazda', 'Hyundai', 'Kia', 'Volvo', 'SEAT', 'Škoda', 'Fiat'
  ];

  const fuelTypes = ['Petrol', 'Diesel', 'Hybrid', 'Electric', 'LPG'];
  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 25 }, (_, i) => currentYear - i);

  const tabs = [
    { id: 'preferences', label: 'Search Preferences' },
    { id: 'notifications', label: 'Notifications' },
  ];

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto">
      <h1 className="text-3xl font-bold text-gray-900 mb-8">Settings</h1>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-8">
        <nav className="-mb-px flex space-x-8">
          {tabs.map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`py-2 px-1 border-b-2 font-medium text-sm transition-colors ${
                activeTab === tab.id
                  ? 'border-blue-500 text-blue-600'
                  : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </nav>
      </div>

      <form onSubmit={handleSubmit} className="space-y-8">
        {activeTab === 'preferences' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Search Preferences</h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              {/* Price Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Price Range (€)
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <input
                    type="number"
                    value={formData.min_price}
                    onChange={(e) => handleInputChange('min_price', e.target.value)}
                    placeholder="Min price"
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                  <input
                    type="number"
                    value={formData.max_price}
                    onChange={(e) => handleInputChange('max_price', e.target.value)}
                    placeholder="Max price"
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  />
                </div>
              </div>

              {/* Max Mileage */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Mileage (km)
                </label>
                <input
                  type="number"
                  value={formData.max_mileage}
                  onChange={(e) => handleInputChange('max_mileage', e.target.value)}
                  placeholder="e.g. 150000"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>

              {/* Year Range */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Year Range
                </label>
                <div className="grid grid-cols-2 gap-3">
                  <select
                    value={formData.min_year}
                    onChange={(e) => handleInputChange('min_year', e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Min Year</option>
                    {years.reverse().map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                  <select
                    value={formData.max_year}
                    onChange={(e) => handleInputChange('max_year', e.target.value)}
                    className="px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    <option value="">Max Year</option>
                    {years.reverse().map(year => (
                      <option key={year} value={year}>{year}</option>
                    ))}
                  </select>
                </div>
              </div>

              {/* Max Distance */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Max Distance (km)
                </label>
                <input
                  type="number"
                  value={formData.max_distance_km}
                  onChange={(e) => handleInputChange('max_distance_km', e.target.value)}
                  placeholder="e.g. 50"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* Preferred Makes */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preferred Car Makes
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {carMakes.map(make => (
                  <label key={make} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.preferred_makes.includes(make)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          handleInputChange('preferred_makes', [...formData.preferred_makes, make]);
                        } else {
                          handleInputChange('preferred_makes', formData.preferred_makes.filter(m => m !== make));
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">{make}</span>
                  </label>
                ))}
              </div>
            </div>

            {/* Preferred Fuel Types */}
            <div className="mt-6">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Preferred Fuel Types
              </label>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
                {fuelTypes.map(fuel => (
                  <label key={fuel} className="flex items-center">
                    <input
                      type="checkbox"
                      checked={formData.preferred_fuel_types.includes(fuel)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          handleInputChange('preferred_fuel_types', [...formData.preferred_fuel_types, fuel]);
                        } else {
                          handleInputChange('preferred_fuel_types', formData.preferred_fuel_types.filter(f => f !== fuel));
                        }
                      }}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm text-gray-700">{fuel}</span>
                  </label>
                ))}
              </div>
            </div>
          </div>
        )}

        {activeTab === 'notifications' && (
          <div className="bg-white rounded-lg border border-gray-200 p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-6">Notification Settings</h2>

            <div className="space-y-6">
              {/* Email Notifications */}
              <div>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={formData.email_notifications}
                    onChange={(e) => handleInputChange('email_notifications', e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-700">
                    Enable email notifications
                  </span>
                </label>
                <p className="mt-1 text-sm text-gray-500">
                  Receive email alerts when new cars matching your preferences are found.
                </p>
              </div>

              {/* Notification Frequency */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Notification Frequency
                </label>
                <select
                  value={formData.notification_frequency}
                  onChange={(e) => handleInputChange('notification_frequency', e.target.value)}
                  disabled={!formData.email_notifications}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
                >
                  <option value="instant">Instant (as soon as found)</option>
                  <option value="daily">Daily digest</option>
                  <option value="weekly">Weekly digest</option>
                </select>
                <p className="mt-1 text-sm text-gray-500">
                  Choose how often you want to receive notifications about new car matches.
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Save Button */}
        <div className="flex justify-end">
          <button
            type="submit"
            disabled={updatePreferencesMutation.isLoading}
            className="bg-blue-600 hover:bg-blue-700 text-white px-6 py-2 rounded-md font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {updatePreferencesMutation.isLoading ? (
              <div className="flex items-center">
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </div>
            ) : (
              'Save Preferences'
            )}
          </button>
        </div>
      </form>
    </div>
  );
};

export default Settings;