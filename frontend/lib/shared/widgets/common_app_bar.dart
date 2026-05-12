// lib/shared/widgets/common_app_bar.dart
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';

class CommonAppBar extends StatelessWidget implements PreferredSizeWidget {
  final String title;
  final List<Widget>? actions;
  final bool showBackButton;

  const CommonAppBar({
    super.key,
    required this.title,
    this.actions,
    this.showBackButton = false,
  });

  @override
  Size get preferredSize => const Size.fromHeight(kToolbarHeight);

  @override
  Widget build(BuildContext context) {
    return AppBar(
      leading: showBackButton
          ? IconButton(
              icon: const Icon(Icons.arrow_back_ios_new_rounded),
              onPressed: () => context.pop(),
            )
          : Padding(
              padding: const EdgeInsets.only(left: 8),
              child: IconButton(
                icon: CircleAvatar(
                  radius: 18,
                  backgroundColor: AppTheme.surfaceVariant,
                  child: const Icon(
                    Icons.person_outline_rounded,
                    color: AppTheme.primary,
                    size: 20,
                  ),
                ),
                onPressed: () => context.push('/settings'),
              ),
            ),
      title: Text(title),
      actions: [
        // App logo top-right
        Padding(
          padding: const EdgeInsets.only(right: 12),
          child: actions != null
              ? Row(children: actions!)
              : _AppLogo(),
        ),
      ],
    );
  }
}

class _AppLogo extends StatelessWidget {
  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 5),
      decoration: BoxDecoration(
        color: AppTheme.primary,
        borderRadius: BorderRadius.circular(10),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: const [
          Icon(Icons.eco_rounded, color: Colors.white, size: 16),
          SizedBox(width: 4),
          Text(
            'NutriAI',
            style: TextStyle(
              color: Colors.white,
              fontSize: 13,
              fontWeight: FontWeight.w700,
              fontFamily: 'Inter',
            ),
          ),
        ],
      ),
    );
  }
}
