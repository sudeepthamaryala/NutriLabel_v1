// lib/features/onboarding/health_profile_screen.dart
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/theme.dart';
import '../../shared/models/health_profile.dart';
import '../../shared/providers/profile_provider.dart';
import '../../shared/widgets/loading_overlay.dart';

class HealthProfileScreen extends ConsumerStatefulWidget {
  const HealthProfileScreen({super.key});
  @override
  ConsumerState<HealthProfileScreen> createState() => _HealthProfileScreenState();
}

class _HealthProfileScreenState extends ConsumerState<HealthProfileScreen> {
  final _pageCtrl = PageController();
  int _page = 0;
  final int _totalPages = 6;

  // Form values
  int _age = 25;
  double _weight = 70;
  double _height = 170;
  Sex _sex = Sex.male;
  ActivityLevel _activity = ActivityLevel.moderate;
  HealthGoal _goal = HealthGoal.weight_maintenance;
  final List<String> _allergies = [];
  final List<String> _diseases = [];
  final _allergyCtrl = TextEditingController();
  final _diseaseCtrl = TextEditingController();

  @override
  void dispose() {
    _pageCtrl.dispose();
    _allergyCtrl.dispose();
    _diseaseCtrl.dispose();
    super.dispose();
  }

  void _next() {
    if (_page < _totalPages - 1) {
      _pageCtrl.nextPage(duration: const Duration(milliseconds: 350), curve: Curves.easeInOut);
      setState(() => _page++);
    } else {
      _save();
    }
  }

  void _back() {
    if (_page > 0) {
      _pageCtrl.previousPage(duration: const Duration(milliseconds: 350), curve: Curves.easeInOut);
      setState(() => _page--);
    }
  }

  Future<void> _save() async {
    final profile = HealthProfile(
      age: _age, weightKg: _weight, heightCm: _height,
      sex: _sex, activityLevel: _activity, goal: _goal,
      allergies: _allergies, diseases: _diseases,
    );
    final ok = await ref.read(profileProvider.notifier).save(profile);
    if (ok && mounted) context.go('/home');
    else if (mounted) {
      final err = ref.read(profileProvider).error ?? 'Failed to save profile';
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(err), backgroundColor: AppTheme.error),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final isLoading = ref.watch(profileProvider).isLoading;
    return LoadingOverlay(
      isLoading: isLoading,
      message: 'Saving your profile…',
      child: Scaffold(
        backgroundColor: AppTheme.surface,
        body: SafeArea(
          child: Column(
            children: [
              _Header(page: _page, total: _totalPages, onBack: _back),
              Expanded(
                child: PageView(
                  controller: _pageCtrl,
                  physics: const NeverScrollableScrollPhysics(),
                  children: [
                    _AgeStep(age: _age, onChanged: (v) => setState(() => _age = v)),
                    _WeightStep(weight: _weight, onChanged: (v) => setState(() => _weight = v)),
                    _HeightStep(height: _height, onChanged: (v) => setState(() => _height = v)),
                    _SexActivityStep(
                      sex: _sex, activity: _activity,
                      onSex: (v) => setState(() => _sex = v),
                      onActivity: (v) => setState(() => _activity = v),
                    ),
                    _GoalStep(goal: _goal, onChanged: (v) => setState(() => _goal = v)),
                    _AllergiesDiseasesStep(
                      allergies: _allergies, diseases: _diseases,
                      allergyCtrl: _allergyCtrl, diseaseCtrl: _diseaseCtrl,
                      onAddAllergy: (s) => setState(() => _allergies.add(s)),
                      onRemoveAllergy: (i) => setState(() => _allergies.removeAt(i)),
                      onAddDisease: (s) => setState(() => _diseases.add(s)),
                      onRemoveDisease: (i) => setState(() => _diseases.removeAt(i)),
                    ),
                  ],
                ),
              ),
              _Footer(page: _page, total: _totalPages, onNext: _next),
            ],
          ),
        ),
      ),
    );
  }
}

class _Header extends StatelessWidget {
  final int page, total;
  final VoidCallback onBack;
  const _Header({required this.page, required this.total, required this.onBack});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 12, 24, 0),
      child: Column(
        children: [
          Row(
            children: [
              if (page > 0)
                IconButton(
                  icon: const Icon(Icons.arrow_back_ios_new_rounded),
                  onPressed: onBack,
                )
              else
                const SizedBox(width: 48),
              Expanded(
                child: Text(
                  'Set Up Your Profile',
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 17, fontWeight: FontWeight.w700),
                ),
              ),
              Text(
                '${page + 1}/$total',
                style: const TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 13),
              ),
            ],
          ),
          const SizedBox(height: 10),
          LinearProgressIndicator(
            value: (page + 1) / total,
            backgroundColor: AppTheme.divider,
            color: AppTheme.primary,
            borderRadius: BorderRadius.circular(4),
            minHeight: 5,
          ),
        ],
      ),
    );
  }
}

class _Footer extends StatelessWidget {
  final int page, total;
  final VoidCallback onNext;
  const _Footer({required this.page, required this.total, required this.onNext});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: FilledButton(
        onPressed: onNext,
        child: Text(page == total - 1 ? 'Save Profile' : 'Continue'),
      ),
    );
  }
}

// ── Step widgets ─────────────────────────────────────────────────────────────

class _AgeStep extends StatelessWidget {
  final int age;
  final ValueChanged<int> onChanged;
  const _AgeStep({required this.age, required this.onChanged});

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.cake_outlined,
    title: 'How old are you?',
    subtitle: 'Helps personalise your nutrition targets',
    child: Column(
      children: [
        Text('$age years', style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: AppTheme.primary)),
        Slider(
          value: age.toDouble(), min: 10, max: 100, divisions: 90,
          activeColor: AppTheme.primary,
          onChanged: (v) => onChanged(v.round()),
        ),
      ],
    ),
  );
}

class _WeightStep extends StatelessWidget {
  final double weight;
  final ValueChanged<double> onChanged;
  const _WeightStep({required this.weight, required this.onChanged});

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.monitor_weight_outlined,
    title: 'What\'s your weight?',
    subtitle: 'Used to calculate your daily caloric needs',
    child: Column(
      children: [
        Text('${weight.toStringAsFixed(1)} kg', style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: AppTheme.primary)),
        Slider(
          value: weight, min: 30, max: 250, divisions: 220,
          activeColor: AppTheme.primary,
          onChanged: onChanged,
        ),
      ],
    ),
  );
}

class _HeightStep extends StatelessWidget {
  final double height;
  final ValueChanged<double> onChanged;
  const _HeightStep({required this.height, required this.onChanged});

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.height_rounded,
    title: 'What\'s your height?',
    subtitle: 'Used to calculate your BMI',
    child: Column(
      children: [
        Text('${height.toStringAsFixed(0)} cm', style: const TextStyle(fontSize: 32, fontWeight: FontWeight.w700, color: AppTheme.primary)),
        Slider(
          value: height, min: 100, max: 250, divisions: 150,
          activeColor: AppTheme.primary,
          onChanged: onChanged,
        ),
      ],
    ),
  );
}

class _SexActivityStep extends StatelessWidget {
  final Sex sex;
  final ActivityLevel activity;
  final ValueChanged<Sex> onSex;
  final ValueChanged<ActivityLevel> onActivity;
  const _SexActivityStep({required this.sex, required this.activity, required this.onSex, required this.onActivity});

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.people_outline_rounded,
    title: 'About you',
    subtitle: 'Biological sex and activity level',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text('Sex', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        Wrap(
          spacing: 8,
          children: Sex.values.map((s) => ChoiceChip(
            label: Text(s.label),
            selected: sex == s,
            onSelected: (_) => onSex(s),
            selectedColor: AppTheme.primary,
            labelStyle: TextStyle(color: sex == s ? Colors.white : AppTheme.onSurface),
          )).toList(),
        ),
        const SizedBox(height: 20),
        const Text('Activity Level', style: TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 10),
        ...ActivityLevel.values.map((a) => RadioListTile<ActivityLevel>(
          value: a, groupValue: activity,
          title: Text(a.label, style: const TextStyle(fontSize: 14)),
          activeColor: AppTheme.primary,
          contentPadding: EdgeInsets.zero,
          onChanged: (v) => onActivity(v!),
        )),
      ],
    ),
  );
}

class _GoalStep extends StatelessWidget {
  final HealthGoal goal;
  final ValueChanged<HealthGoal> onChanged;
  const _GoalStep({required this.goal, required this.onChanged});

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.flag_outlined,
    title: 'What\'s your goal?',
    subtitle: 'We\'ll tailor advice to match your target',
    child: Column(
      children: HealthGoal.values.map((g) => Card(
        margin: const EdgeInsets.only(bottom: 12),
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(12),
          side: BorderSide(color: goal == g ? AppTheme.primary : AppTheme.divider, width: goal == g ? 2 : 1),
        ),
        child: ListTile(
          title: Text(g.label, style: const TextStyle(fontWeight: FontWeight.w600)),
          leading: Radio<HealthGoal>(value: g, groupValue: goal, activeColor: AppTheme.primary, onChanged: (v) => onChanged(v!)),
          onTap: () => onChanged(g),
        ),
      )).toList(),
    ),
  );
}

class _AllergiesDiseasesStep extends StatelessWidget {
  final List<String> allergies, diseases;
  final TextEditingController allergyCtrl, diseaseCtrl;
  final ValueChanged<String> onAddAllergy, onAddDisease;
  final ValueChanged<int> onRemoveAllergy, onRemoveDisease;
  const _AllergiesDiseasesStep({
    required this.allergies, required this.diseases,
    required this.allergyCtrl, required this.diseaseCtrl,
    required this.onAddAllergy, required this.onRemoveAllergy,
    required this.onAddDisease, required this.onRemoveDisease,
  });

  @override
  Widget build(BuildContext context) => _StepWrapper(
    icon: Icons.health_and_safety_outlined,
    title: 'Health Details',
    subtitle: 'Optional — helps us flag harmful ingredients',
    child: Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _ChipInput(label: 'Allergies', ctrl: allergyCtrl, items: allergies, onAdd: onAddAllergy, onRemove: onRemoveAllergy),
        const SizedBox(height: 20),
        _ChipInput(label: 'Medical Conditions', ctrl: diseaseCtrl, items: diseases, onAdd: onAddDisease, onRemove: onRemoveDisease),
      ],
    ),
  );
}

class _ChipInput extends StatelessWidget {
  final String label;
  final TextEditingController ctrl;
  final List<String> items;
  final ValueChanged<String> onAdd;
  final ValueChanged<int> onRemove;
  const _ChipInput({required this.label, required this.ctrl, required this.items, required this.onAdd, required this.onRemove});

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
        const SizedBox(height: 8),
        Row(
          children: [
            Expanded(
              child: TextField(
                controller: ctrl,
                decoration: InputDecoration(hintText: 'Add $label…', contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10)),
              ),
            ),
            const SizedBox(width: 8),
            IconButton.filled(
              onPressed: () {
                final v = ctrl.text.trim();
                if (v.isNotEmpty) { onAdd(v); ctrl.clear(); }
              },
              icon: const Icon(Icons.add),
              style: IconButton.styleFrom(backgroundColor: AppTheme.primary),
            ),
          ],
        ),
        if (items.isNotEmpty) ...[
          const SizedBox(height: 10),
          Wrap(
            spacing: 8, runSpacing: 6,
            children: items.asMap().entries.map((e) => Chip(
              label: Text(e.value, style: const TextStyle(fontSize: 13)),
              deleteIcon: const Icon(Icons.close, size: 14),
              onDeleted: () => onRemove(e.key),
              backgroundColor: AppTheme.primary.withOpacity(0.1),
            )).toList(),
          ),
        ],
      ],
    );
  }
}

class _StepWrapper extends StatelessWidget {
  final IconData icon;
  final String title, subtitle;
  final Widget child;
  const _StepWrapper({required this.icon, required this.title, required this.subtitle, required this.child});

  @override
  Widget build(BuildContext context) {
    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const SizedBox(height: 16),
          Container(
            width: 56, height: 56,
            decoration: BoxDecoration(color: AppTheme.primary.withOpacity(0.1), borderRadius: BorderRadius.circular(16)),
            child: Icon(icon, color: AppTheme.primary, size: 28),
          ),
          const SizedBox(height: 20),
          Text(title, style: const TextStyle(fontSize: 22, fontWeight: FontWeight.w700)),
          const SizedBox(height: 6),
          Text(subtitle, style: const TextStyle(color: AppTheme.onSurfaceMuted, fontSize: 14)),
          const SizedBox(height: 32),
          child,
        ],
      ),
    );
  }
}
