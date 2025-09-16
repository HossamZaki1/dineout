import 'dart:convert';
import 'dart:io';
import 'package:flutter/foundation.dart';
import 'package:http/http.dart' as http;
import '../models/restaurant_model.dart';

class DiscoveryService {
  static String get baseUrl {
    if (kIsWeb) return 'http://localhost:8000';
    if (!kIsWeb && Platform.isAndroid) return 'http://10.0.2.2:8000';
    return 'http://127.0.0.1:8000';
  }

  /// Discover restaurants near user location
  Future<List<RestaurantModel>> discoverRestaurants({
    double? latitude,
    double? longitude,
    int radius = 5000,
    int limit = 10,
  }) async {
    final response = await http
        .get(
          Uri.parse(
            '$baseUrl/api/discovery/restaurants'
            '?lat=$latitude&lng=$longitude&radius=$radius&limit=$limit',
          ),
          headers: {'Content-Type': 'application/json'},
        )
        .timeout(const Duration(seconds: 10));

    if (response.statusCode == 200) {
      final data = json.decode(response.body);
      final restaurants = (data['restaurants'] as List)
          .map((json) => RestaurantModel.fromJson(json))
          .toList();

      return restaurants;
    } else {
      throw Exception('Failed to load restaurants: ${response.statusCode}');
    }
  }
}
