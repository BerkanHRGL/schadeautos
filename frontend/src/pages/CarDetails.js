import React from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery } from 'react-query';
import { carsAPI } from '../services/api';
import { CalendarIcon, MapPinIcon, ArrowTopRightOnSquareIcon, ArrowLeftIcon } from '@heroicons/react/24/outline';
import { formatDistance } from 'date-fns';

const CarDetails = () => {
  const { id } = useParams();

  const { data: car, isLoading, error } = useQuery(
    ['car', id],
    () => carsAPI.getCar(id).then(res => res.data),
    {
      enabled: !!id,
    }
  );

  const formatPrice = (price) => {
    if (!price) return 'Contact seller';
    return new Intl.NumberFormat('nl-NL', {
      style: 'currency',
      currency: 'EUR',
      maximumFractionDigits: 0,
    }).format(price);
  };

  const formatMileage = (mileage) => {
    if (!mileage) return 'Unknown';
    return new Intl.NumberFormat('nl-NL').format(mileage) + ' km';
  };

  if (isLoading) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/4 mb-6"></div>
          <div className="h-64 bg-gray-200 rounded mb-6"></div>
          <div className="space-y-4">
            <div className="h-4 bg-gray-200 rounded w-3/4"></div>
            <div className="h-4 bg-gray-200 rounded w-1/2"></div>
            <div className="h-4 bg-gray-200 rounded w-2/3"></div>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <div className="text-red-600 mb-4">
          <svg className="w-12 h-12 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
        </div>
        <h2 className="text-xl font-semibold text-gray-900 mb-2">Car Not Found</h2>
        <p className="text-gray-600 mb-4">The car you're looking for doesn't exist or has been removed.</p>
        <Link
          to="/"
          className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors"
        >
          Back to Dashboard
        </Link>
      </div>
    );
  }

  if (!car) return null;

  return (
    <div className="max-w-4xl mx-auto">
      {/* Back Button */}
      <Link
        to="/"
        className="flex items-center text-blue-600 hover:text-blue-800 mb-6 transition-colors"
      >
        <ArrowLeftIcon className="w-5 h-5 mr-2" />
        Back to Dashboard
      </Link>

      {/* Header */}
      <div className="bg-white rounded-lg shadow-md overflow-hidden mb-6">
        <div className="p-6">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                {car.title || `${car.make} ${car.model || ''} (${car.year || 'Unknown'})`}
              </h1>
              <div className="flex items-center space-x-4 text-gray-600">
                <span className="bg-green-100 text-green-800 text-sm font-medium px-2 py-1 rounded">
                  {car.source_website}
                </span>
                <span className="flex items-center">
                  <CalendarIcon className="w-4 h-4 mr-1" />
                  Added {formatDistance(new Date(car.first_seen), new Date(), { addSuffix: true })}
                </span>
              </div>
            </div>
            <div className="text-right">
              <div className="text-3xl font-bold text-green-600 mb-2">
                {formatPrice(car.price)}
              </div>
              <a
                href={car.url}
                target="_blank"
                rel="noopener noreferrer"
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-md transition-colors flex items-center"
              >
                View Original Listing
                <ArrowTopRightOnSquareIcon className="w-4 h-4 ml-2" />
              </a>
            </div>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Images */}
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Images</h2>
            {car.images && car.images.length > 0 ? (
              <div className="space-y-4">
                {car.images.map((image, index) => (
                  <img
                    key={index}
                    src={image}
                    alt={`${car.make} ${car.model} ${index + 1}`}
                    className="w-full h-64 object-cover rounded-lg"
                    onError={(e) => {
                      e.target.style.display = 'none';
                    }}
                  />
                ))}
              </div>
            ) : (
              <div className="h-64 bg-gray-200 rounded-lg flex items-center justify-center">
                <span className="text-gray-500">No images available</span>
              </div>
            )}
          </div>
        </div>

        {/* Details */}
        <div className="space-y-6">
          {/* Car Specifications */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Specifications</h2>
            <div className="grid grid-cols-2 gap-4">
              {car.make && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Make</span>
                  <span className="text-gray-900">{car.make}</span>
                </div>
              )}
              {car.model && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Model</span>
                  <span className="text-gray-900">{car.model}</span>
                </div>
              )}
              {car.year && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Year</span>
                  <span className="text-gray-900">{car.year}</span>
                </div>
              )}
              <div>
                <span className="block text-sm font-medium text-gray-700">Mileage</span>
                <span className="text-gray-900">{formatMileage(car.mileage)}</span>
              </div>
              {car.fuel_type && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Fuel Type</span>
                  <span className="text-gray-900">{car.fuel_type}</span>
                </div>
              )}
              {car.transmission && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Transmission</span>
                  <span className="text-gray-900">{car.transmission}</span>
                </div>
              )}
              {car.color && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Color</span>
                  <span className="text-gray-900">{car.color}</span>
                </div>
              )}
              {car.location && (
                <div>
                  <span className="block text-sm font-medium text-gray-700">Location</span>
                  <span className="text-gray-900 flex items-center">
                    <MapPinIcon className="w-4 h-4 mr-1" />
                    {car.location}
                  </span>
                </div>
              )}
            </div>
          </div>

          {/* Damage Information */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-xl font-semibold text-gray-900 mb-4">Damage Information</h2>

            {car.damage_keywords && car.damage_keywords.length > 0 && (
              <div className="mb-4">
                <span className="block text-sm font-medium text-gray-700 mb-2">Damage Type</span>
                <div className="flex flex-wrap gap-2">
                  {car.damage_keywords.map((keyword, index) => (
                    <span
                      key={index}
                      className="bg-orange-100 text-orange-800 text-sm font-medium px-2 py-1 rounded"
                    >
                      {keyword}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {car.damage_description && (
              <div>
                <span className="block text-sm font-medium text-gray-700 mb-2">Description</span>
                <p className="text-gray-900 whitespace-pre-wrap">{car.damage_description}</p>
              </div>
            )}

            <div className="mt-4">
              <div className="flex items-center">
                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                  car.has_cosmetic_damage_only
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                }`}>
                  {car.has_cosmetic_damage_only ? 'Cosmetic damage only' : 'May have structural damage'}
                </span>
              </div>
            </div>
          </div>

          {/* Contact Information */}
          {car.contact_info && Object.keys(car.contact_info).length > 0 && (
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold text-gray-900 mb-4">Contact Information</h2>
              <div className="space-y-2">
                {car.contact_info.phone && (
                  <div>
                    <span className="block text-sm font-medium text-gray-700">Phone</span>
                    <a
                      href={`tel:${car.contact_info.phone}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      {car.contact_info.phone}
                    </a>
                  </div>
                )}
                {car.contact_info.email && (
                  <div>
                    <span className="block text-sm font-medium text-gray-700">Email</span>
                    <a
                      href={`mailto:${car.contact_info.email}`}
                      className="text-blue-600 hover:text-blue-800"
                    >
                      {car.contact_info.email}
                    </a>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Full Description */}
      {car.description && (
        <div className="bg-white rounded-lg shadow-md p-6 mt-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">Full Description</h2>
          <p className="text-gray-900 whitespace-pre-wrap leading-relaxed">
            {car.description}
          </p>
        </div>
      )}
    </div>
  );
};

export default CarDetails;