import 'package:flutter/material.dart';
import '../models/restaurant_model.dart';
import '../services/discovery_service.dart';
import '../services/location_service.dart';

class DiscoveryScreen extends StatefulWidget {
  const DiscoveryScreen({super.key});

  @override
  State<DiscoveryScreen> createState() => _DiscoveryScreenState();
}

class _DiscoveryScreenState extends State<DiscoveryScreen>
    with TickerProviderStateMixin {
  late AnimationController _slidingController;
  late Animation<double> _slideAnimation;

  final DiscoveryService _discoveryService = DiscoveryService();
  List<DishItem> _dishes = [];
  bool _isLoading = true;
  String? _errorMessage;
  double? _userLatitude;
  double? _userLongitude;

  @override
  void initState() {
    super.initState();

    // Initialize sliding animation
    _slidingController = AnimationController(
      duration: const Duration(seconds: 20),
      vsync: this,
    );

    _slideAnimation = Tween<double>(begin: 0.0, end: 1.0).animate(
      CurvedAnimation(parent: _slidingController, curve: Curves.linear),
    );

    // Load restaurant data
    _loadRestaurants();
  }

  Future<void> _loadRestaurants() async {
    try {
      setState(() {
        _isLoading = true;
        _errorMessage = null;
      });

      // Get user location first
      final position = await LocationService.getCurrentLocation();
      if (position != null) {
        _userLatitude = position.latitude;
        _userLongitude = position.longitude;
        print('Using user location: $_userLatitude, $_userLongitude');
      } else {
        print('Could not get user location, using default coordinates');
        // Show a snackbar to inform user about location
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            const SnackBar(
              content: Text('Location access denied. Using default location.'),
              duration: Duration(seconds: 3),
            ),
          );
        }
      }

      final restaurants = await _discoveryService.discoverRestaurants(
        latitude: _userLatitude,
        longitude: _userLongitude,
      );

      // Convert restaurants to dish items for sliding animation
      final List<DishItem> dishes = [];
      final List<Color> colors = [
        Colors.red.shade400,
        Colors.orange.shade400,
        Colors.blue.shade400,
        Colors.green.shade400,
        Colors.brown.shade400,
        Colors.purple.shade400,
        Colors.cyan.shade400,
        Colors.pink.shade400,
      ];

      for (int i = 0; i < restaurants.length; i++) {
        final restaurant = restaurants[i];
        final featuredDish = restaurant.featuredDish;

        if (featuredDish != null) {
          dishes.add(
            DishItem(
              featuredDish.name,
              restaurant.name,
              colors[i % colors.length],
              restaurant: restaurant,
              dish: featuredDish,
            ),
          );
        }
      }

      setState(() {
        _dishes = dishes;
        _isLoading = false;
      });

      // Start the continuous sliding animation after data is loaded
      if (_dishes.isNotEmpty) {
        _slidingController.repeat();
      }
    } catch (e) {
      setState(() {
        _isLoading = false;
        _errorMessage =
            'Failed to load restaurants. Please check your connection.';
      });
      print('Error loading restaurants: $e');
    }
  }

  @override
  void dispose() {
    _slidingController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [
              Colors.deepOrange.shade50,
              Colors.orange.shade50,
              Colors.yellow.shade50,
            ],
          ),
        ),
        child: SafeArea(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              // Header
              Padding(
                padding: const EdgeInsets.all(24.0),
                child: Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          'Discover',
                          style: Theme.of(context).textTheme.headlineLarge
                              ?.copyWith(
                                fontWeight: FontWeight.bold,
                                color: Colors.deepOrange.shade700,
                              ),
                        ),
                        Text(
                          _userLatitude != null && _userLongitude != null
                              ? 'Popular dishes near you'
                              : 'Popular dishes (using default location)',
                          style: Theme.of(context).textTheme.bodyLarge
                              ?.copyWith(color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                    Container(
                      decoration: BoxDecoration(
                        color: Colors.white,
                        borderRadius: BorderRadius.circular(12),
                        boxShadow: [
                          BoxShadow(
                            color: Colors.black.withOpacity(0.1),
                            blurRadius: 8,
                            offset: const Offset(0, 2),
                          ),
                        ],
                      ),
                      child: IconButton(
                        onPressed: _loadRestaurants,
                        icon: const Icon(
                          Icons.refresh,
                          color: Colors.deepOrange,
                        ),
                      ),
                    ),
                  ],
                ),
              ),

              // Sliding dishes bar
              SizedBox(
                height: 120,
                child: _isLoading
                    ? const Center(
                        child: CircularProgressIndicator(
                          valueColor: AlwaysStoppedAnimation<Color>(
                            Colors.deepOrange,
                          ),
                        ),
                      )
                    : _dishes.isEmpty
                    ? Center(
                        child: Column(
                          mainAxisAlignment: MainAxisAlignment.center,
                          children: [
                            Icon(
                              Icons.restaurant_menu,
                              color: Colors.grey.shade400,
                              size: 32,
                            ),
                            const SizedBox(height: 8),
                            Text(
                              _errorMessage ?? 'No dishes found',
                              style: TextStyle(
                                color: Colors.grey.shade600,
                                fontSize: 14,
                              ),
                            ),
                            if (_errorMessage != null) ...[
                              const SizedBox(height: 8),
                              TextButton(
                                onPressed: _loadRestaurants,
                                child: const Text('Retry'),
                              ),
                            ],
                          ],
                        ),
                      )
                    : AnimatedBuilder(
                        animation: _slideAnimation,
                        builder: (context, child) {
                          return ListView.builder(
                            scrollDirection: Axis.horizontal,
                            physics: const NeverScrollableScrollPhysics(),
                            itemCount:
                                _dishes.length *
                                3, // Repeat for continuous scroll
                            itemBuilder: (context, index) {
                              final dishIndex = index % _dishes.length;
                              final dish = _dishes[dishIndex];

                              // Calculate position for smooth sliding
                              final itemWidth = 200.0;
                              final totalWidth = _dishes.length * itemWidth;
                              final offset = _slideAnimation.value * totalWidth;
                              final position = (index * itemWidth) - offset;

                              return Transform.translate(
                                offset: Offset(position, 0),
                                child: Container(
                                  width: itemWidth,
                                  margin: const EdgeInsets.only(right: 16),
                                  child: _buildDishCard(dish),
                                ),
                              );
                            },
                          );
                        },
                      ),
              ),

              const SizedBox(height: 32),

              // Main content area
              Expanded(
                child: Padding(
                  padding: const EdgeInsets.symmetric(horizontal: 24.0),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'What are you craving?',
                        style: Theme.of(context).textTheme.headlineSmall
                            ?.copyWith(
                              fontWeight: FontWeight.bold,
                              color: Colors.grey.shade800,
                            ),
                      ),
                      const SizedBox(height: 24),

                      // Category buttons
                      Wrap(
                        spacing: 12,
                        runSpacing: 12,
                        children: [
                          _buildCategoryChip(
                            '🍕 Pizza',
                            Colors.red.shade100,
                            Colors.red.shade700,
                          ),
                          _buildCategoryChip(
                            '🍔 Burgers',
                            Colors.orange.shade100,
                            Colors.orange.shade700,
                          ),
                          _buildCategoryChip(
                            '🍜 Asian',
                            Colors.blue.shade100,
                            Colors.blue.shade700,
                          ),
                          _buildCategoryChip(
                            '🥗 Healthy',
                            Colors.green.shade100,
                            Colors.green.shade700,
                          ),
                          _buildCategoryChip(
                            '🍰 Desserts',
                            Colors.pink.shade100,
                            Colors.pink.shade700,
                          ),
                          _buildCategoryChip(
                            '☕ Coffee',
                            Colors.brown.shade100,
                            Colors.brown.shade700,
                          ),
                        ],
                      ),

                      const SizedBox(height: 32),

                      // Action buttons
                      Row(
                        children: [
                          Expanded(
                            child: ElevatedButton.icon(
                              onPressed: () {
                                // TODO: Navigate to search/chat
                              },
                              icon: const Icon(Icons.search),
                              label: const Text('Search Now'),
                              style: ElevatedButton.styleFrom(
                                backgroundColor: Colors.deepOrange,
                                foregroundColor: Colors.white,
                                padding: const EdgeInsets.symmetric(
                                  vertical: 16,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(width: 16),
                          Expanded(
                            child: OutlinedButton.icon(
                              onPressed: () {
                                // TODO: Navigate to map view
                              },
                              icon: const Icon(Icons.map),
                              label: const Text('Map View'),
                              style: OutlinedButton.styleFrom(
                                padding: const EdgeInsets.symmetric(
                                  vertical: 16,
                                ),
                                shape: RoundedRectangleBorder(
                                  borderRadius: BorderRadius.circular(12),
                                ),
                              ),
                            ),
                          ),
                        ],
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

  Widget _buildDishCard(DishItem dish) {
    return GestureDetector(
      onTap: () {
        if (dish.restaurant != null && dish.dish != null) {
          _showDishDetails(dish.restaurant!, dish.dish!);
        } else {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: Text(
                'Selected: ${dish.dishName} at ${dish.restaurantName}',
              ),
              duration: const Duration(seconds: 2),
            ),
          );
        }
      },
      child: Container(
        decoration: BoxDecoration(
          gradient: LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [dish.color, dish.color.withOpacity(0.8)],
          ),
          borderRadius: BorderRadius.circular(16),
          boxShadow: [
            BoxShadow(
              color: dish.color.withOpacity(0.3),
              blurRadius: 8,
              offset: const Offset(0, 4),
            ),
          ],
        ),
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Text(
              dish.dishName,
              style: const TextStyle(
                color: Colors.white,
                fontSize: 16,
                fontWeight: FontWeight.bold,
              ),
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            const SizedBox(height: 4),
            Row(
              children: [
                const Icon(Icons.restaurant, color: Colors.white70, size: 14),
                const SizedBox(width: 4),
                Expanded(
                  child: Text(
                    dish.restaurantName,
                    style: const TextStyle(color: Colors.white70, fontSize: 12),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                  ),
                ),
              ],
            ),
            if (dish.dish?.price != null) ...[
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                decoration: BoxDecoration(
                  color: Colors.white.withOpacity(0.2),
                  borderRadius: BorderRadius.circular(8),
                ),
                child: Text(
                  dish.dish!.price!,
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 11,
                    fontWeight: FontWeight.w600,
                  ),
                ),
              ),
            ],
          ],
        ),
      ),
    );
  }

  void _showDishDetails(RestaurantModel restaurant, DishModel dish) {
    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      backgroundColor: Colors.transparent,
      builder: (context) => Container(
        height: MediaQuery.of(context).size.height * 0.5,
        decoration: const BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
        ),
        child: Column(
          children: [
            Container(
              margin: const EdgeInsets.only(top: 12),
              width: 40,
              height: 4,
              decoration: BoxDecoration(
                color: Colors.grey.shade300,
                borderRadius: BorderRadius.circular(2),
              ),
            ),
            Expanded(
              child: Padding(
                padding: const EdgeInsets.all(20),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      dish.name,
                      style: Theme.of(context).textTheme.headlineSmall
                          ?.copyWith(fontWeight: FontWeight.bold),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      restaurant.name,
                      style: TextStyle(
                        color: Colors.grey.shade600,
                        fontSize: 16,
                      ),
                    ),
                    if (dish.price != null) ...[
                      const SizedBox(height: 12),
                      Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 12,
                          vertical: 6,
                        ),
                        decoration: BoxDecoration(
                          color: Colors.green.shade50,
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: Colors.green.shade200),
                        ),
                        child: Text(
                          'Price: ${dish.price}',
                          style: TextStyle(
                            color: Colors.green.shade700,
                            fontWeight: FontWeight.w600,
                            fontSize: 16,
                          ),
                        ),
                      ),
                    ],
                    const SizedBox(height: 16),
                    Row(
                      children: [
                        Icon(
                          Icons.star,
                          color: Colors.orange.shade400,
                          size: 16,
                        ),
                        const SizedBox(width: 4),
                        Text(
                          '${restaurant.rating} (${restaurant.totalRatings} reviews)',
                          style: TextStyle(color: Colors.grey.shade600),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Text(
                      restaurant.address,
                      style: TextStyle(color: Colors.grey.shade600),
                    ),
                    const Spacer(),
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: () {
                          Navigator.pop(context);
                        },
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.deepOrange,
                          foregroundColor: Colors.white,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(12),
                          ),
                        ),
                        child: const Text('Close'),
                      ),
                    ),
                  ],
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildCategoryChip(
    String label,
    Color backgroundColor,
    Color textColor,
  ) {
    return GestureDetector(
      onTap: () {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Selected category: $label'),
            duration: const Duration(seconds: 1),
          ),
        );
      },
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
        decoration: BoxDecoration(
          color: backgroundColor,
          borderRadius: BorderRadius.circular(20),
          border: Border.all(color: textColor.withOpacity(0.3)),
        ),
        child: Text(
          label,
          style: TextStyle(color: textColor, fontWeight: FontWeight.w500),
        ),
      ),
    );
  }
}

class DishItem {
  final String dishName;
  final String restaurantName;
  final Color color;
  final RestaurantModel? restaurant;
  final DishModel? dish;

  DishItem(
    this.dishName,
    this.restaurantName,
    this.color, {
    this.restaurant,
    this.dish,
  });
}
