import 'package:flutter/material.dart';

import 'labels.dart';
import 'theme.dart';

/// Fades and slides a child in once, staggered by [index]. Skipped when the OS asks for less motion.
class Reveal extends StatelessWidget {
  const Reveal({super.key, required this.child, this.index = 0});

  final Widget child;
  final int index;

  @override
  Widget build(BuildContext context) {
    if (MediaQuery.of(context).disableAnimations) return child;
    return TweenAnimationBuilder<double>(
      tween: Tween(begin: 0, end: 1),
      duration: Duration(milliseconds: 380 + index * 60),
      curve: Curves.easeOutCubic,
      builder: (_, t, c) => Opacity(opacity: t, child: Transform.translate(offset: Offset(0, (1 - t) * 14), child: c)),
      child: child,
    );
  }
}

/// A dark header with a rendered 3D object (assets/images, made by apps/console/scripts/render-assets.mjs).
class HeroHeader extends StatelessWidget {
  const HeroHeader({super.key, required this.title, this.subtitle, this.image, this.trailing, this.imageSize = 120});

  final String title;
  final String? subtitle;
  final String? image;
  final Widget? trailing;
  final double imageSize;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: const EdgeInsets.only(bottom: 8),
      padding: const EdgeInsets.fromLTRB(20, 20, 12, 20),
      decoration: BoxDecoration(
        borderRadius: BorderRadius.circular(24),
        gradient: const LinearGradient(colors: [AppColors.ink900, AppColors.ink700], begin: Alignment.topLeft, end: Alignment.bottomRight),
        boxShadow: [BoxShadow(color: AppColors.ink900.withValues(alpha: 0.16), blurRadius: 24, spreadRadius: -8, offset: const Offset(0, 12))],
      ),
      child: Row(children: [
        Expanded(
          child: Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
            Text(title, style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: Colors.white)),
            if (subtitle != null) ...[
              const SizedBox(height: 6),
              Text(subtitle!, style: TextStyle(color: Colors.white.withValues(alpha: 0.72), fontSize: 13.5, height: 1.35)),
            ],
            if (trailing != null) ...[const SizedBox(height: 14), trailing!],
          ]),
        ),
        if (image != null) Image.asset(image!, width: imageSize, height: imageSize, fit: BoxFit.contain, semanticLabel: ''),
      ]),
    );
  }
}

/// A coloured pill for a canonical application state.
class StatePill extends StatelessWidget {
  const StatePill(this.state, {super.key});

  final String state;

  static Color colorFor(String state) => switch (state) {
        'CREDITED' => AppColors.teal,
        'DEFICIENCY_RAISED' || 'PAYMENT_FAILED' || 'REJECTED' => AppColors.rose,
        'SANCTIONED' || 'PAYMENT_INITIATED' => const Color(0xFF6366F1),
        'DRAFT' => AppColors.muted,
        _ => AppColors.saffron,
      };

  @override
  Widget build(BuildContext context) {
    final c = colorFor(state);
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
      decoration: BoxDecoration(color: c.withValues(alpha: 0.12), borderRadius: BorderRadius.circular(99)),
      child: Text(stateLabel(state), style: TextStyle(color: c, fontSize: 12, fontWeight: FontWeight.w600)),
    );
  }
}

/// Where an application is in the canonical lifecycle, as six steps. The state comes from the ledger.
class StageTracker extends StatelessWidget {
  const StageTracker(this.state, {super.key});

  final String state;
  static const _steps = ['Applied', 'Institute', 'District', 'Sanctioned', 'Paid', 'Credited'];

  int get _index => switch (state) {
        'DRAFT' => -1,
        'SUBMITTED' => 0,
        'INSTITUTE_VERIFICATION' || 'DEFICIENCY_RAISED' || 'RESUBMITTED' => 1,
        'AUTHORITY_VERIFICATION' => 2,
        'SANCTIONED' => 3,
        'PAYMENT_INITIATED' || 'PAYMENT_FAILED' => 4,
        'CREDITED' || 'RENEWAL_DUE' => 5,
        _ => 0,
      };

  bool get _problem => state == 'DEFICIENCY_RAISED' || state == 'PAYMENT_FAILED' || state == 'REJECTED';

  @override
  Widget build(BuildContext context) {
    final current = _index;
    return Semantics(
      label: 'Stage: ${stateLabel(state)}',
      child: Column(children: [
        Row(children: [
          for (var i = 0; i < _steps.length; i++) ...[
            _Dot(done: i < current || (i == current && state == 'CREDITED'), active: i == current, problem: i == current && _problem),
            if (i < _steps.length - 1)
              Expanded(child: Container(height: 3, margin: const EdgeInsets.symmetric(horizontal: 3),
                  decoration: BoxDecoration(borderRadius: BorderRadius.circular(2),
                      color: i < current ? AppColors.teal : AppColors.line))),
          ],
        ]),
        const SizedBox(height: 6),
        Row(mainAxisAlignment: MainAxisAlignment.spaceBetween, children: [
          for (var i = 0; i < _steps.length; i++)
            Text(_steps[i], style: TextStyle(fontSize: 10.5, color: i == current ? AppColors.text : AppColors.muted,
                fontWeight: i == current ? FontWeight.w600 : FontWeight.w500)),
        ]),
      ]),
    );
  }
}

class _Dot extends StatelessWidget {
  const _Dot({required this.done, required this.active, required this.problem});

  final bool done;
  final bool active;
  final bool problem;

  @override
  Widget build(BuildContext context) {
    final color = problem ? AppColors.rose : done ? AppColors.teal : active ? AppColors.saffron : AppColors.line;
    return AnimatedContainer(
      duration: const Duration(milliseconds: 300),
      width: active ? 18 : 14,
      height: active ? 18 : 14,
      decoration: BoxDecoration(
        shape: BoxShape.circle,
        color: done || active || problem ? color : Colors.white,
        border: Border.all(color: color, width: 2),
        boxShadow: active ? [BoxShadow(color: color.withValues(alpha: 0.35), blurRadius: 10)] : null,
      ),
      child: done ? const Icon(Icons.check, size: 10, color: Colors.white) : null,
    );
  }
}

/// A big figure with a label, used on money and summary cards.
class Figure extends StatelessWidget {
  const Figure({super.key, required this.label, required this.value, this.color = AppColors.text});

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) => Column(crossAxisAlignment: CrossAxisAlignment.start, children: [
        Text(label.toUpperCase(), style: const TextStyle(fontSize: 11, letterSpacing: 0.6, color: AppColors.muted, fontWeight: FontWeight.w600)),
        const SizedBox(height: 4),
        Text(value, style: TextStyle(fontSize: 22, fontWeight: FontWeight.w700, color: color, letterSpacing: -0.4,
            fontFeatures: const [FontFeature.tabularFigures()])),
      ]);
}
