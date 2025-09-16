class DishModel {
  final String name;
  final String? price;
  final int mentionsCount;

  const DishModel({
    required this.name,
    this.price,
    required this.mentionsCount,
  });

  factory DishModel.fromJson(Map<String, dynamic> json) {
    return DishModel(
      name: json['name'] ?? '',
      price: json['price'],
      mentionsCount: json['mentions_count'] ?? 0,
    );
  }
}

class RestaurantModel {
  final String placeId;
  final String name;
  final String address;
  final double rating;
  final int totalRatings;
  final int? priceLevel;
  final List<String> cuisineTypes;
  final String? phoneNumber;
  final double lat;
  final double lng;
  final List<String> photos;
  final List<DishModel> topDishes;

  const RestaurantModel({
    required this.placeId,
    required this.name,
    required this.address,
    required this.rating,
    required this.totalRatings,
    this.priceLevel,
    required this.cuisineTypes,
    this.phoneNumber,
    required this.lat,
    required this.lng,
    required this.photos,
    required this.topDishes,
  });

  factory RestaurantModel.fromJson(Map<String, dynamic> json) {
    final location = json['location'] ?? {'lat': 0.0, 'lng': 0.0};
    return RestaurantModel(
      placeId: json['place_id'] ?? '',
      name: json['name'] ?? '',
      address: json['address'] ?? '',
      rating: (json['rating'] as num?)?.toDouble() ?? 0.0,
      totalRatings: json['total_ratings'] ?? 0,
      priceLevel: json['price_level'],
      cuisineTypes: List<String>.from(json['cuisine_types'] ?? []),
      phoneNumber: json['phone_number'],
      lat: (location['lat'] as num).toDouble(),
      lng: (location['lng'] as num).toDouble(),
      photos: List<String>.from(json['photos'] ?? []),
      topDishes:
          (json['top_dishes'] as List<dynamic>?)
              ?.map((dish) => DishModel.fromJson(dish))
              .toList() ??
          [],
    );
  }

  /// Get the most popular dish
  DishModel? get featuredDish {
    if (topDishes.isEmpty) return null;
    return topDishes.first;
  }

  /// Get cuisine types as formatted string
  String get cuisineTypesFormatted {
    if (cuisineTypes.isEmpty) return 'Restaurant';
    return cuisineTypes.take(2).join(' • ');
  }
}
