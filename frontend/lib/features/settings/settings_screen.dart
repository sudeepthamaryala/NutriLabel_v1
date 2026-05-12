// lib/features/settings/settings_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import '../../app/theme.dart';
import '../../shared/providers/auth_provider.dart';
import '../../shared/providers/profile_provider.dart';
import '../../shared/widgets/bottom_nav_bar.dart';
import '../../shared/widgets/common_app_bar.dart';
import '../../shared/widgets/loading_overlay.dart';

class SettingsScreen extends ConsumerWidget {
  const SettingsScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final authState = ref.watch(authProvider);
    final profileState = ref.watch(profileProvider);
    final user = authState.user;

    return LoadingOverlay(
      isLoading: authState.isLoading,
      message: 'Signing out…',
      child: Scaffold(
        backgroundColor: AppTheme.surface,
        appBar: const CommonAppBar(title: 'Settings'),
        bottomNavigationBar: const AppBottomNavBar(currentIndex: 2),
        body: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            // Profile card
            _ProfileCard(
              name: user?.fullName ?? '—',
              email: user?.email ?? '—',
              onEdit: () => context.push('/onboarding'),
            ),
            const SizedBox(height: 20),

            // Account section
            _SectionHeader('Account'),
            _SettingsTile(icon: Icons.person_outlined, title: 'Full Name', subtitle: user?.fullName, onTap: null),
            _SettingsTile(icon: Icons.email_outlined, title: 'Email', subtitle: user?.email, onTap: null),
            const SizedBox(height: 16),

            // Health profile section
            _SectionHeader('Health Profile'),
            _SettingsTile(
              icon: Icons.monitor_heart_outlined,
              title: 'Edit Health Profile',
              subtitle: profileState.profile != null ? 'Age ${profileState.profile!.age} · ${profileState.profile!.weightKg.toStringAsFixed(0)} kg' : 'Not set up yet',
              onTap: () => context.push('/onboarding'),
            ),
            const SizedBox(height: 16),

            // App section
            _SectionHeader('App'),
            _SettingsTile(icon: Icons.info_outline_rounded, title: 'About NutriLabel AI', subtitle: 'Version 1.0.0', onTap: () {
              showAboutDialog(
                context: context,
                applicationName: 'NutriLabel AI',
                applicationVersion: '1.0.0',
                applicationLegalese: '© 2026 NutriLabel AI. All rights reserved.',
              );
            }),
            const SizedBox(height: 16),

            // Danger zone
            _SectionHeader('Account Actions'),
            Card(
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(14),
                side: BorderSide(color: AppTheme.error.withOpacity(0.3)),
              ),
              child: ListTile(
                leading: Container(
                  width: 40, height: 40,
                  decoration: BoxDecoration(color: AppTheme.error.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
                  child: const Icon(Icons.logout_rounded, color: AppTheme.error, size: 20),
                ),
                title: const Text('Sign Out', style: TextStyle(color: AppTheme.error, fontWeight: FontWeight.w600)),
                trailing: const Icon(Icons.arrow_forward_ios_rounded, size: 13, color: AppTheme.error),
                onTap: () => _confirmSignOut(context, ref),
              ),
            ),
            const SizedBox(height: 32),
          ],
        ),
      ),
    );
  }

  Future<void> _confirmSignOut(BuildContext context, WidgetRef ref) async {
    final confirm = await showDialog<bool>(
      context: context,
      builder: (_) => AlertDialog(
        title: const Text('Sign Out'),
        content: const Text('Are you sure you want to sign out?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Cancel')),
          FilledButton(
            onPressed: () => Navigator.pop(context, true),
            style: FilledButton.styleFrom(backgroundColor: AppTheme.error),
            child: const Text('Sign Out'),
          ),
        ],
      ),
    );
    if (confirm == true) {
      await ref.read(authProvider.notifier).signOut();
    }
  }
}

class _ProfileCard extends StatelessWidget {
  final String name, email;
  final VoidCallback onEdit;
  const _ProfileCard({required this.name, required this.email, required this.onEdit});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        gradient: const LinearGradient(colors: [AppTheme.primary, AppTheme.primaryLight], begin: Alignment.topLeft, end: Alignment.bottomRight),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Row(children: [
        CircleAvatar(radius: 28, backgroundColor: Colors.white.withOpacity(0.2), child: Text(name.isNotEmpty ? name[0].toUpperCase() : '?', style: const TextStyle(color: Colors.white, fontSize: 22, fontWeight: FontWeight.w700))),
        const SizedBox(width: 16),
        Expanded(child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
          Text(name, style: const TextStyle(color: Colors.white, fontSize: 17, fontWeight: FontWeight.w700)),
          const SizedBox(height: 2),
          Text(email, style: const TextStyle(color: Colors.white70, fontSize: 12)),
        ])),
        IconButton(icon: const Icon(Icons.edit_rounded, color: Colors.white70), onPressed: onEdit),
      ]),
    );
  }
}

class _SectionHeader extends StatelessWidget {
  final String title;
  const _SectionHeader(this.title);
  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8, left: 4),
      child: Text(title.toUpperCase(), style: const TextStyle(fontSize: 11, fontWeight: FontWeight.w700, color: AppTheme.onSurfaceMuted, letterSpacing: 0.8)),
    );
  }
}

class _SettingsTile extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final VoidCallback? onTap;
  const _SettingsTile({required this.icon, required this.title, this.subtitle, this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Container(
          width: 40, height: 40,
          decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(10)),
          child: Icon(icon, color: AppTheme.primary, size: 20),
        ),
        title: Text(title, style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 14)),
        subtitle: subtitle != null ? Text(subtitle!, style: const TextStyle(fontSize: 12, color: AppTheme.onSurfaceMuted)) : null,
        trailing: onTap != null ? const Icon(Icons.arrow_forward_ios_rounded, size: 13, color: AppTheme.onSurfaceMuted) : null,
        onTap: onTap,
      ),
    );
  }
}
