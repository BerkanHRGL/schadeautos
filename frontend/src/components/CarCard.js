import React from 'react';
import { Link } from 'react-router-dom';
import { CalendarIcon, MapPinIcon } from '@heroicons/react/24/outline';
import { formatDistance } from 'date-fns';

const CarCard = ({ car }) => {
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

  const getImageUrl = (car) => {
    if (car.images && car.images.length > 0) {
      return car.images[0];
    }
    // Use a placeholder image from a reliable source
    return 'https://via.placeholder.com/400x200/e5e7eb/6b7280?text=No+Image+Available';
  };

  const getDamageTypes = (keywords) => {
    if (!keywords || keywords.length === 0) return [];

    // Map keywords to user-friendly damage types
    const damageTypeMap = {
      'cosmetische schade': 'Cosmetic',
      'lichte schade': 'Minor',
      'lakschade': 'Paint',
      'deukjes': 'Dents',
      'krassen': 'Scratches',
      'hagelschade': 'Hail',
      'parkeerdeuk': 'Parking',
      'bumperdeuk': 'Bumper',
      'cosmetic damage': 'Cosmetic',
      'minor damage': 'Minor',
      'paint damage': 'Paint',
      'scratch': 'Scratches',
      'dent': 'Dents',
    };

    const types = keywords
      .map(keyword => damageTypeMap[keyword.toLowerCase()])
      .filter(Boolean)
      .slice(0, 3); // Show max 3 types

    return [...new Set(types)]; // Remove duplicates
  };

  const damageTypes = getDamageTypes(car.damage_keywords);

  const getDealRatingColor = (rating) => {
    switch (rating?.toLowerCase()) {
      case 'excellent':
        return 'bg-green-100 text-green-800';
      case 'good':
        return 'bg-blue-100 text-blue-800';
      case 'fair':
        return 'bg-yellow-100 text-yellow-800';
      case 'poor':
        return 'bg-red-100 text-red-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const formatProfitPercentage = (percentage) => {
    if (!percentage) return null;
    return `${percentage.toFixed(1)}% below market`;
  };

  return (
    <div className="bg-white rounded-lg shadow-md overflow-hidden hover:shadow-lg transition-shadow duration-200">
      {/* Image */}
      <div className="relative h-48 bg-gray-200">
        <img
          src={getImageUrl(car)}
          alt={`${car.make} ${car.model}`}
          className="w-full h-full object-cover"
          onError={(e) => {
            e.target.src = 'https://via.placeholder.com/400x200/e5e7eb/6b7280?text=No+Image+Available';
          }}
        />
        <div className="absolute top-2 right-2">
          <span className="bg-green-100 text-green-800 text-xs font-medium px-2 py-1 rounded-full">
            {car.source_website}
          </span>
        </div>
      </div>

      {/* Content */}
      <div className="p-4">
        {/* Title */}
        <h3 className="text-lg font-semibold text-gray-900 mb-2 line-clamp-2">
          {car.title || `${car.make} ${car.model || ''} (${car.year || 'Unknown'})`}
        </h3>

        {/* Car Details */}
        <div className="space-y-2 mb-3">
          <div className="flex items-center justify-between">
            <span className="text-2xl font-bold text-green-600">
              {formatPrice(car.price)}
            </span>
            {car.year && (
              <span className="text-sm text-gray-500">{car.year}</span>
            )}
          </div>

          {/* Deal Rating */}
          {car.deal_rating && (
            <div className="flex items-center justify-between">
              <span className={`text-xs font-medium px-2 py-1 rounded-full ${getDealRatingColor(car.deal_rating)}`}>
                {car.deal_rating.charAt(0).toUpperCase() + car.deal_rating.slice(1)} Deal
              </span>
              {car.profit_percentage && (
                <span className="text-xs text-gray-500">
                  {formatProfitPercentage(car.profit_percentage)}
                </span>
              )}
            </div>
          )}

          <div className="flex items-center text-sm text-gray-600">
            <span className="font-medium">{formatMileage(car.mileage)}</span>
            {car.location && (
              <>
                <span className="mx-2">•</span>
                <MapPinIcon className="w-4 h-4 mr-1" />
                <span className="truncate">{car.location}</span>
              </>
            )}
          </div>
        </div>

        {/* Damage Types */}
        {damageTypes.length > 0 && (
          <div className="flex flex-wrap gap-1 mb-3">
            {damageTypes.map((type, index) => (
              <span
                key={index}
                className="bg-orange-100 text-orange-800 text-xs font-medium px-2 py-1 rounded"
              >
                {type}
              </span>
            ))}
          </div>
        )}

        {/* Damage Description */}
        {car.damage_description && (
          <p className="text-sm text-gray-600 mb-3 line-clamp-2">
            {car.damage_description}
          </p>
        )}

        {/* Footer */}
        <div className="flex items-center justify-between pt-3 border-t border-gray-100">
          <span className="text-xs text-gray-500 flex items-center">
            <CalendarIcon className="w-4 h-4 mr-1" />
            {formatDistance(new Date(car.first_seen), new Date(), { addSuffix: true })}
          </span>

          <div className="flex space-x-2">
            <a
              href={car.url}
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 text-sm font-medium"
            >
              View Listing
            </a>
            <Link
              to={`/car/${car.id}`}
              className="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded text-sm font-medium transition-colors"
            >
              Details
            </Link>
          </div>
        </div>
      </div>
    </div>
  );
};

export default CarCard;