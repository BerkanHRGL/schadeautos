import React, { useState, useEffect } from 'react';
import { XMarkIcon, AdjustmentsHorizontalIcon } from '@heroicons/react/24/outline';

const FilterPanel = ({ filters, onFiltersChange, isOpen, onToggle }) => {
  const [localFilters, setLocalFilters] = useState(filters);

  useEffect(() => {
    setLocalFilters(filters);
  }, [filters]);

  const handleChange = (key, value) => {
    const newFilters = { ...localFilters, [key]: value };
    setLocalFilters(newFilters);
    onFiltersChange(newFilters);
  };

  const resetFilters = () => {
    const resetFilters = {
      min_price: '',
      max_price: '',
      max_mileage: '',
      min_year: '',
      max_year: '',
      make: '',
      search: '',
      cosmetic_only: true,
    };
    setLocalFilters(resetFilters);
    onFiltersChange(resetFilters);
  };

  const carMakes = [
    'Audi', 'BMW', 'Mercedes-Benz', 'Volkswagen', 'Opel', 'Ford',
    'Renault', 'Peugeot', 'Citroën', 'Toyota', 'Nissan', 'Honda',
    'Mazda', 'Hyundai', 'Kia', 'Volvo', 'SEAT', 'Škoda', 'Fiat'
  ];

  const currentYear = new Date().getFullYear();
  const years = Array.from({ length: 25 }, (_, i) => currentYear - i);

  if (!isOpen) {
    return (
      <button
        onClick={onToggle}
        className="fixed top-20 left-4 z-10 bg-white shadow-lg rounded-lg p-3 border border-gray-200 hover:bg-gray-50 transition-colors"
      >
        <AdjustmentsHorizontalIcon className="w-6 h-6 text-gray-600" />
      </button>
    );
  }

  return (
    <div className="fixed inset-y-0 left-0 z-20 w-80 bg-white shadow-xl border-r border-gray-200 overflow-y-auto">
      <div className="p-6">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-900">Filters</h2>
          <button
            onClick={onToggle}
            className="p-1 rounded-md text-gray-400 hover:text-gray-600"
          >
            <XMarkIcon className="w-6 h-6" />
          </button>
        </div>

        {/* Search */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Search
          </label>
          <input
            type="text"
            value={localFilters.search || ''}
            onChange={(e) => handleChange('search', e.target.value)}
            placeholder="Search cars..."
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Price Range */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Price Range (€)
          </label>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <input
                type="number"
                value={localFilters.min_price || ''}
                onChange={(e) => handleChange('min_price', e.target.value)}
                placeholder="Min"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
            <div>
              <input
                type="number"
                value={localFilters.max_price || ''}
                onChange={(e) => handleChange('max_price', e.target.value)}
                placeholder="Max"
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              />
            </div>
          </div>
        </div>

        {/* Mileage */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Max Mileage (km)
          </label>
          <input
            type="number"
            value={localFilters.max_mileage || ''}
            onChange={(e) => handleChange('max_mileage', e.target.value)}
            placeholder="e.g. 150000"
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>

        {/* Year Range */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Year Range
          </label>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <select
                value={localFilters.min_year || ''}
                onChange={(e) => handleChange('min_year', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Min Year</option>
                {years.reverse().map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
            <div>
              <select
                value={localFilters.max_year || ''}
                onChange={(e) => handleChange('max_year', e.target.value)}
                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              >
                <option value="">Max Year</option>
                {years.reverse().map(year => (
                  <option key={year} value={year}>{year}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Car Make */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Car Make
          </label>
          <select
            value={localFilters.make || ''}
            onChange={(e) => handleChange('make', e.target.value)}
            className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          >
            <option value="">All Makes</option>
            {carMakes.map(make => (
              <option key={make} value={make}>{make}</option>
            ))}
          </select>
        </div>

        {/* Damage Type */}
        <div className="mb-6">
          <label className="flex items-center">
            <input
              type="checkbox"
              checked={localFilters.cosmetic_only || false}
              onChange={(e) => handleChange('cosmetic_only', e.target.checked)}
              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
            />
            <span className="ml-2 text-sm text-gray-700">
              Cosmetic damage only
            </span>
          </label>
        </div>

        {/* Reset Button */}
        <button
          onClick={resetFilters}
          className="w-full bg-gray-100 hover:bg-gray-200 text-gray-700 py-2 px-4 rounded-md transition-colors"
        >
          Reset Filters
        </button>
      </div>
    </div>
  );
};

export default FilterPanel;