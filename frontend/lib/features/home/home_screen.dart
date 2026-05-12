// lib/features/home/home_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/profile_provider.dart';
import '../../shared/widgets/bottom_nav_bar.dart';
import '../../shared/widgets/common_app_bar.dart';

class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});
  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  @override
  void initState() {
    super.initState();
    Future.microtask(() => ref.read(profileProvider.notifier).load());
  }

  @override
  Widget build(BuildContext context) {
    final user = ref.watch(authProvider).user;
    final profile = ref.watch(profileProvider).profile;
    final firstName = user?.fullName.split(' ').first ?? 'there';

    return Scaffold(
      backgroundColor: AppTheme.surface,
      appBar: const CommonAppBar(title: 'Home'),
      bottomNavigationBar: const AppBottomNavBar(currentIndex: 0),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            // Greeting
            _GreetingCard(name: firstName),
            const SizedBox(height: 24),

            // Profile nudge
            if (profile == null) ...[
              _ProfileNudge(),
              const SizedBox(height: 24),
            ],

            const Text(
              'What would you like to do?',
              style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 14),

            // Feature cards
            _FeatureCard(
              icon: Icons.camera_alt_rounded,
              color: AppTheme.primary,
              title: 'Analyse Label',
              subtitle: 'Photograph a nutrition label and get instant AI health insights',
              imageAsset: 'assets/images/nutrition_label_sample.png',
              onTap: () => context.push('/analyse'),
            ),
            const SizedBox(height: 14),
            _FeatureCard(
              icon: Icons.compare_arrows_rounded,
              color: AppTheme.accent,
              title: 'Compare Products',
              imageAsset: 'assets/images/product_compare_sample.png',
              subtitle: 'Upload 2–5 products and find the healthiest option',
              onTap: () => context.push('/compare'),
            ),
            const SizedBox(height: 32),

            // Quick stats
            if (profile != null) _StatsRow(profile: profile),
          ],
        ),
      ),
    );
  }
}

class _GreetingCard extends StatelessWidget {
  final String name;
  const _GreetingCard({required this.name});

  String get _greeting {
    final h = DateTime.now().hour;
    if (h < 12) return 'Good morning';
    if (h < 17) return 'Good afternoon';
    return 'Good evening';
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(
          colors: [AppTheme.primary, AppTheme.primaryLight],
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
        ),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Row(
        children: [
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '$_greeting, $name 👋',
                  style: const TextStyle(
                    color: Colors.white,
                    fontSize: 18,
                    fontWeight: FontWeight.w700,
                  ),
                ),
                const SizedBox(height: 6),
                const Text(
                  'Ready to make healthier choices today?',
                  style: TextStyle(color: Colors.white70, fontSize: 13),
                ),
              ],
            ),
          ),
          ClipRRect(
            borderRadius: BorderRadius.circular(16),
            child: Image.asset(
              'assets/images/healthy_meal_overview.png',
              width: 58,
              height: 58,
              fit: BoxFit.cover,
            ),
          ),
        ],
      ),
    );
  }
}

class _ProfileNudge extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: AppTheme.accent.withOpacity(0.1),
        borderRadius: BorderRadius.circular(14),
        border: Border.all(color: AppTheme.accent.withOpacity(0.3)),
      ),
      child: Row(
        children: [
          const Icon(Icons.info_outline_rounded, color: AppTheme.accent),
          const SizedBox(width: 12),
          const Expanded(
            child: Text(
              'Complete your health profile for personalised insights',
              style: TextStyle(fontSize: 13, color: AppTheme.onSurface),
            ),
          ),
          TextButton(
            onPressed: () => context.push('/onboarding'),
            style: TextButton.styleFrom(foregroundColor: AppTheme.accent),
            child: const Text('Set Up'),
          ),
        ],
      ),
    );
  }
}

class _FeatureCard extends StatelessWidget {
  final IconData icon;
  final Color color;
  final String title, subtitle;
  final String imageAsset;
  final VoidCallback onTap;
  const _FeatureCard({
    required this.icon,
    required this.color,
    required this.title,
    required this.subtitle,
    required this.imageAsset,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(20),
        decoration: BoxDecoration(
          color: Colors.white,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: AppTheme.divider),
          boxShadow: [BoxShadow(color: Colors.black.withOpacity(0.04), blurRadius: 8, offset: const Offset(0, 2))],
        ),
        child: Row(
          children: [
            Container(
              width: 52, height: 52,
              clipBehavior: Clip.antiAlias,
              decoration: BoxDecoration(color: color.withOpacity(0.12), borderRadius: BorderRadius.circular(14)),
              child: Stack(
                fit: StackFit.expand,
                children: [
                  Image.asset(imageAsset, fit: BoxFit.cover),
                  ColoredBox(color: color.withOpacity(0.18)),
                  Icon(icon, color: Colors.white, size: 26),
                ],
              ),
            ),
            const SizedBox(width: 16),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(title, style: const TextStyle(fontSize: 16, fontWeight: FontWeight.w700)),
                  const SizedBox(height: 4),
                  Text(subtitle, style: const TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 12, height: 1.4)),
                ],
              ),
            ),
            const Icon(Icons.arrow_forward_ios_rounded, size: 14, color: AppTheme.onSurfaceMuted),
          ],
        ),
      ),
    );
  }
}

class _StatsRow extends StatelessWidget {
  final dynamic profile;
  const _StatsRow({required this.profile});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Your Stats', style: TextStyle(fontSize: 17, fontWeight: FontWeight.w700)),
        const SizedBox(height: 12),
        Row(
          children: [
            Expanded(child: _StatChip(label: 'Age', value: '${profile.age}y')),
            const SizedBox(width: 10),
            Expanded(child: _StatChip(label: 'Weight', value: '${profile.weightKg.toStringAsFixed(0)}kg')),
            const SizedBox(width: 10),
            Expanded(child: _StatChip(label: 'Height', value: '${profile.heightCm.toStringAsFixed(0)}cm')),
          ],
        ),
      ],
    );
  }
}

class _StatChip extends StatelessWidget {
  final String label, value;
  const _StatChip({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 14),
      decoration: BoxDecoration(
        color: Colors.white,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: AppTheme.divider),
      ),
      child: Column(
        children: [
          Text(value, style: const TextStyle(fontSize: 18, fontWeight: FontWeight.w700, color: AppTheme.primary)),
          const SizedBox(height: 2),
          Text(label, style: const TextStyle(fontSize: 11, color: AppTheme.onSurfaceMuted)),
        ],
      ),
    );
  }
}
