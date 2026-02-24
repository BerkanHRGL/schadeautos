import React, { useState, useMemo } from 'react';
import { useQuery } from 'react-query';
import { carsAPI } from '../services/api';
import CarCard from '../components/CarCard';
import FilterPanel from '../components/FilterPanel';
import { ChevronUpDownIcon, Bars3Icon } from '@heroicons/react/24/outline';

const Dashboard = () => {
  const [filters, setFilters] = useState({
    min_price: '',
    max_price: '',
    max_mileage: '',
    min_year: '',
    max_year: '',
    make: '',
    search: '',
    cosmetic_only: true,
    sort_by: 'first_seen',
    sort_order: 'desc',
    skip: 0,
    limit: 100,
  });

  const [filtersOpen, setFiltersOpen] = useState(false);

  // Build query params
  const queryParams = useMemo(() => {
    const params = {};
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== '' && value !== null && value !== undefined) {
        params[key] = value;
      }
    });
    return params;
  }, [filters]);

  const { data: carsData, isLoading, error } = useQuery(
    ['cars', queryParams],
    () => carsAPI.getCars(queryParams).then(res => res.data),
    {
      keepPreviousData: true,
      refetchOnWindowFocus: false,
    }
  );

  const { data: stats } = useQuery(
    'carStats',
    () => carsAPI.getStats().then(res => res.data),
    {
      refetchInterval: 300000, // Refetch every 5 minutes
    }
  );

  const handleFiltersChange = (newFilters) => {
    setFilters(prev => ({ ...prev, ...newFilters, skip: 0 }));
  };

  const handleSortChange = (sortBy) => {
    setFilters(prev => ({
      ...prev,
      sort_by: sortBy,
      sort_order: prev.sort_by === sortBy && prev.sort_order === 'asc' ? 'desc' : 'asc',
    }));
  };

  const sortOptions = [
    { key: 'first_seen', label: 'Date Added' },
    { key: 'price', label: 'Price' },
    { key: 'mileage', label: 'Mileage' },
    { key: 'year', label: 'Year' },
  ];

  if (error) {
    return (
      <div className="text-center py-12">
        <div className="text-red-600 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Error Loading Cars</h2>
        <p className="text-gray-600">Please try again later.</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <FilterPanel
        filters={filters}
        onFiltersChange={handleFiltersChange}
        isOpen={filtersOpen}
        onToggle={() => setFiltersOpen(!filtersOpen)}
      />

      <div className={`transition-all duration-300 ${filtersOpen ? 'ml-80' : 'ml-0'}`}>
        <div className="container mx-auto px-4 py-8">
          {/* Header */}
          <div className="mb-8">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h1 className="text-3xl font-bold text-gray-900">Car Damage Finder</h1>
                <p className="text-gray-600 mt-1">
                  Find cars with cosmetic damage at great prices
                </p>
              </div>

              {!filtersOpen && (
                <button
                  onClick={() => setFiltersOpen(true)}
                  className="bg-white shadow-md rounded-lg px-4 py-2 border border-gray-200 hover:bg-gray-50 transition-colors flex items-center space-x-2"
                >
                  <Bars3Icon className="w-5 h-5 text-gray-600" />
                  <span className="text-gray-700">Filters</span>
                </button>
              )}
            </div>

            {/* Live Scraping Notice */}
            <div className="mb-6 bg-green-50 border border-green-200 rounded-lg p-4">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-green-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-green-800">
                    Live Scraping Active
                  </h3>
                  <div className="mt-1 text-sm text-green-700">
                    <p>
                      Showing real car listings scraped from Marktplaats under €10,000 with damage keywords.
                      The scraper runs automatically every 2 hours to find new listings.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Stats */}
            {stats && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-blue-600">{stats.total_cars}</div>
                  <div className="text-sm text-gray-600">Total Cars</div>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-green-600">{stats.cosmetic_damage_only}</div>
                  <div className="text-sm text-gray-600">Cosmetic Only</div>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-purple-600">€{stats.average_price.toLocaleString()}</div>
                  <div className="text-sm text-gray-600">Average Price</div>
                </div>
                <div className="bg-white rounded-lg p-4 border border-gray-200">
                  <div className="text-2xl font-bold text-orange-600">{stats.unique_makes}</div>
                  <div className="text-sm text-gray-600">Car Brands</div>
                </div>
              </div>
            )}

            {/* Sort Options */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {carsData ? `${carsData.length} cars found` : ''}
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-sm text-gray-600">Sort by:</span>
                <div className="flex space-x-1">
                  {sortOptions.map(option => (
                    <button
                      key={option.key}
                      onClick={() => handleSortChange(option.key)}
                      className={`px-3 py-1 rounded-md text-sm font-medium transition-colors flex items-center space-x-1 ${
                        filters.sort_by === option.key
                          ? 'bg-blue-100 text-blue-700'
                          : 'text-gray-600 hover:text-gray-900'
                      }`}
                    >
                      <span>{option.label}</span>
                      {filters.sort_by === option.key && (
                        <ChevronUpDownIcon className="w-4 h-4" />
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          {/* Cars Grid */}
          {isLoading ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {Array.from({ length: 8 }).map((_, index) => (
                <div key={index} className="bg-white rounded-lg shadow-md overflow-hidden animate-pulse">
                  <div className="h-48 bg-gray-200"></div>
                  <div className="p-4">
                    <div className="h-4 bg-gray-200 rounded mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded mb-2 w-3/4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/2"></div>
                  </div>
                </div>
              ))}
            </div>
          ) : carsData && carsData.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
              {carsData.map((car) => (
                <CarCard key={car.id} car={car} />
              ))}
            </div>
          ) : (
            <div className="text-center py-12">
              <div className="text-gray-400 mb-4">
                <svg className="w-16 h-16 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
              </div>
              <h2 className="text-xl font-semibold text-gray-900 mb-2">No Cars Found</h2>
              <p className="text-gray-600 mb-4">Try adjusting your filters to see more results.</p>
              <button
                onClick={() => handleFiltersChange({
                  min_price: '',
                  max_price: '',
                  max_mileage: '',
                  min_year: '',
                  max_year: '',
                  make: '',
                  search: '',
                  cosmetic_only: true,
                })}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
              >
                Reset Filters
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Dashboard;