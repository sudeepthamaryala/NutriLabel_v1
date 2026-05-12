// lib/shared/widgets/cross_platform_image.dart
import 'dart:io';
import 'dart:typed_data';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';

/// Renders an image from either [bytes] (web) or [file] (mobile).
///
/// On Flutter Web, [Image.file] throws an assertion error because dart:io
/// File is not supported in the browser. This widget automatically selects
/// the correct image source based on [kIsWeb]:
///   - Web   → [Image.memory] from [bytes]  (Uint8List from XFile.readAsBytes)
///   - Mobile → [Image.file]  from [file]   (dart:io File)
///
/// Usage:
///   CrossPlatformImage(
///     file: _file,          // non-null on mobile
///     bytes: _bytes,        // non-null on web
///     width: 180, height: 180, fit: BoxFit.cover,
///   )
class CrossPlatformImage extends StatelessWidget {
  final File? file;
  final Uint8List? bytes;
  final double? width;
  final double? height;
  final BoxFit fit;

  const CrossPlatformImage({
    super.key,
    this.file,
    this.bytes,
    this.width,
    this.height,
    this.fit = BoxFit.cover,
  }) : assert(
          file != null || bytes != null,
          'Either file (mobile) or bytes (web) must be provided.',
        );

  @override
  Widget build(BuildContext context) {
    if (kIsWeb) {
      // Web: bytes must be provided (from XFile.readAsBytes())
      if (bytes == null) {
        return _placeholder();
      }
      return Image.memory(
        bytes!,
        width: width,
        height: height,
        fit: fit,
        errorBuilder: (_, __, ___) => _placeholder(),
      );
    } else {
      // Mobile: file must be provided (File(xfile.path))
      if (file == null) {
        return _placeholder();
      }
      return Image.file(
        file!,
        width: width,
        height: height,
        fit: fit,
        errorBuilder: (_, __, ___) => _placeholder(),
      );
    }
  }

  Widget _placeholder() {
    return SizedBox(
      width: width,
      height: height,
      child: const Center(
        child: Icon(Icons.broken_image_outlined, color: Colors.grey),
      ),
    );
  }
}

/// A lightweight container that holds an image in a cross-platform way.
///
/// On web, only [bytes] is populated.
/// On mobile, only [file] is populated.
/// [name] is the original filename (used as multipart upload filename).
class PickedImage {
  final File? file;
  final Uint8List? bytes;
  final String name;

  const PickedImage({
    this.file,
    this.bytes,
    required this.name,
  });

  bool get isValid => kIsWeb ? bytes != null : file != null;

  /// Picks an image from [XFile] and stores the right representation.
  static Future<PickedImage> fromXFile(dynamic xfile) async {
    final filename = (xfile.path as String).split('/').last;
    if (kIsWeb) {
      final b = await xfile.readAsBytes() as Uint8List;
      return PickedImage(bytes: b, name: filename);
    } else {
      return PickedImage(file: File(xfile.path as String), name: filename);
    }
  }
}
