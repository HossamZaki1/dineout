import 'package:flutter/material.dart';
import '../models/chat.dart';
import 'restaurant_photo.dart';

class RestaurantCard extends StatelessWidget {
  final RestaurantInfo restaurant;
  final VoidCallback onTap;
  const RestaurantCard({
    super.key,
    required this.restaurant,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    final status = restaurant.isOpenNow == null
        ? 'Hours not available'
        : restaurant.isOpenNow == true
        ? 'OPEN'
        : restaurant.nextOpeningDisplay ?? 'CLOSED';
    return SizedBox(
      width: 260,
      child: Card(
        clipBehavior: Clip.antiAlias,
        child: InkWell(
          onTap: onTap,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              SizedBox(
                height: 120,
                width: double.infinity,
                child: restaurant.photoUrls.isEmpty
                    ? const Center(child: Icon(Icons.camera_alt))
                    : RestaurantPhoto(reference: restaurant.photoUrls.first),
              ),
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.all(8),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        restaurant.name,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(fontWeight: FontWeight.bold),
                      ),
                      const SizedBox(height: 4),
                      Text(
                        restaurant.address,
                        maxLines: 2,
                        overflow: TextOverflow.ellipsis,
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      const SizedBox(height: 4),
                      Row(
                        children: [
                          const Icon(Icons.star, color: Colors.amber, size: 16),
                          Text(' ${restaurant.rating}'),
                          const SizedBox(width: 8),
                          Expanded(
                            child: Text(
                              status,
                              maxLines: 2,
                              style: TextStyle(
                                fontSize: 12,
                                fontWeight: FontWeight.bold,
                                color: restaurant.isOpenNow == true
                                    ? Colors.green
                                    : Colors.orange.shade700,
                              ),
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Expanded(
                        child: SingleChildScrollView(
                          child: Text(
                            restaurant.summary,
                            style: Theme.of(context).textTheme.bodySmall,
                          ),
                        ),
                      ),
                    ],
                  ),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
