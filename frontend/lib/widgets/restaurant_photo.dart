import 'package:flutter/material.dart';
import '../services/photo_service.dart';

class RestaurantPhoto extends StatefulWidget {
  final String reference;
  final double? width;
  final double? height;
  final BoxFit fit;
  const RestaurantPhoto({
    super.key,
    required this.reference,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
  });

  @override
  State<RestaurantPhoto> createState() => _RestaurantPhotoState();
}

class _RestaurantPhotoState extends State<RestaurantPhoto> {
  late Future<String> _url;

  @override
  void initState() {
    super.initState();
    _url = PhotoService.instance.resolve(widget.reference);
  }

  @override
  void didUpdateWidget(RestaurantPhoto oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.reference != widget.reference) {
      _url = PhotoService.instance.resolve(widget.reference);
    }
  }

  @override
  Widget build(BuildContext context) => SizedBox(
    width: widget.width,
    height: widget.height,
    child: FutureBuilder<String>(
      future: _url,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: Icon(Icons.restaurant));
        }
        return Image.network(
          snapshot.data!,
          width: widget.width,
          height: widget.height,
          fit: widget.fit,
          errorBuilder: (context, error, stack) =>
              const Center(child: Icon(Icons.broken_image)),
        );
      },
    ),
  );
}
