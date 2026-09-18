import 'package:flutter/material.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';

/// Premium high-performance shimmer animation container.
///
/// Wraps a subtree in a single GPU-driven [ShaderMask] with [RepaintBoundary].
/// Animates a continuous smooth sweep with zero widget rebuilds and zero frame jank.
class VyaparShimmer extends StatefulWidget {
  const VyaparShimmer({
    required this.child,
    super.key,
    this.baseColor,
    this.highlightColor,
    this.period = const Duration(milliseconds: 1500),
    this.enabled = true,
  });

  final Widget child;
  final Color? baseColor;
  final Color? highlightColor;
  final Duration period;
  final bool enabled;

  @override
  State<VyaparShimmer> createState() => _VyaparShimmerState();
}

class _VyaparShimmerState extends State<VyaparShimmer>
    with SingleTickerProviderStateMixin {
  late final AnimationController _controller;

  @override
  void initState() {
    super.initState();
    _controller = AnimationController(vsync: this, duration: widget.period);
    if (widget.enabled) {
      _controller.repeat();
    }
  }

  @override
  void didUpdateWidget(covariant VyaparShimmer oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (widget.enabled != oldWidget.enabled) {
      if (widget.enabled) {
        _controller.repeat();
      } else {
        _controller.stop();
      }
    }
  }

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (!widget.enabled) return widget.child;

    final base = widget.baseColor ?? AppColors.outline.withValues(alpha: 0.55);
    final highlight =
        widget.highlightColor ?? Colors.white.withValues(alpha: 0.92);

    return RepaintBoundary(
      child: AnimatedBuilder(
        animation: _controller,
        builder: (context, child) => ShaderMask(
          blendMode: BlendMode.srcATop,
          shaderCallback: (bounds) => LinearGradient(
            begin: Alignment.topLeft,
            end: Alignment.bottomRight,
            colors: [base, highlight, base],
            stops: const [0.0, 0.5, 1.0],
            transform: _SlidingGradientTransform(
              slidePercent: _controller.value,
            ),
          ).createShader(bounds),
          child: child,
        ),
        child: widget.child,
      ),
    );
  }
}

class _SlidingGradientTransform extends GradientTransform {
  const _SlidingGradientTransform({required this.slidePercent});

  final double slidePercent;

  @override
  Matrix4? transform(Rect bounds, {TextDirection? textDirection}) =>
      Matrix4.translationValues(
        bounds.width * (slidePercent * 3.0 - 1.5),
        0.0,
        0.0,
      );
}

/// Primitive skeleton rectangular block.
class SkeletonBox extends StatelessWidget {
  const SkeletonBox({
    super.key,
    this.width,
    this.height = 14,
    this.borderRadius,
    this.color,
  });

  final double? width;
  final double height;
  final BorderRadius? borderRadius;
  final Color? color;

  @override
  Widget build(BuildContext context) => Container(
    width: width,
    height: height,
    decoration: BoxDecoration(
      color: color ?? AppColors.outline.withValues(alpha: 0.65),
      borderRadius: borderRadius ?? BorderRadius.circular(AppRadii.sm),
    ),
  );
}

/// Skeleton text line with rounded pill ends.
class SkeletonLine extends StatelessWidget {
  const SkeletonLine({
    super.key,
    this.width,
    this.height = 14,
    this.borderRadius,
  });

  final double? width;
  final double height;
  final BorderRadius? borderRadius;

  @override
  Widget build(BuildContext context) => SkeletonBox(
    width: width,
    height: height,
    borderRadius: borderRadius ?? BorderRadius.circular(height / 2),
  );
}

/// Skeleton circular shape for avatars, status icons, buttons.
class SkeletonCircle extends StatelessWidget {
  const SkeletonCircle({super.key, this.size = 42});

  final double size;

  @override
  Widget build(BuildContext context) => Container(
    width: size,
    height: size,
    decoration: BoxDecoration(
      color: AppColors.outline.withValues(alpha: 0.65),
      shape: BoxShape.circle,
    ),
  );
}

/// Skeleton capsule / pill for status tags, badges, chips.
class SkeletonPill extends StatelessWidget {
  const SkeletonPill({super.key, this.width = 68, this.height = 24});

  final double width;
  final double height;

  @override
  Widget build(BuildContext context) => SkeletonBox(
    width: width,
    height: height,
    borderRadius: BorderRadius.circular(AppRadii.pill),
  );
}

/// Skeleton bordered card with subtle outline.
class SkeletonCard extends StatelessWidget {
  const SkeletonCard({
    required this.child,
    super.key,
    this.padding = const EdgeInsets.all(AppSpacing.md),
  });

  final Widget child;
  final EdgeInsetsGeometry padding;

  @override
  Widget build(BuildContext context) => Container(
    padding: padding,
    decoration: BoxDecoration(
      color: AppColors.surface,
      borderRadius: BorderRadius.circular(AppRadii.md),
      border: Border.all(color: AppColors.outline.withValues(alpha: 0.6)),
    ),
    child: child,
  );
}

/// Standard skeleton row matching list tiles.
class SkeletonTile extends StatelessWidget {
  const SkeletonTile({
    super.key,
    this.leadingSize = 42,
    this.circular = true,
    this.hasSubtitle = true,
    this.hasTrailing = true,
    this.trailingWidth = 48,
    this.trailingHeight = 22,
  });

  final double leadingSize;
  final bool circular;
  final bool hasSubtitle;
  final bool hasTrailing;
  final double trailingWidth;
  final double trailingHeight;

  @override
  Widget build(BuildContext context) => Padding(
    padding: const EdgeInsets.symmetric(vertical: 8),
    child: Row(
      children: [
        if (circular)
          SkeletonCircle(size: leadingSize)
        else
          SkeletonBox(
            width: leadingSize,
            height: leadingSize,
            borderRadius: BorderRadius.circular(AppRadii.sm),
          ),
        const SizedBox(width: AppSpacing.md),
        Expanded(
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              const SkeletonLine(width: 140, height: 16),
              if (hasSubtitle) ...[
                const SizedBox(height: 7),
                const SkeletonLine(width: 90, height: 12),
              ],
            ],
          ),
        ),
        if (hasTrailing) ...[
          const SizedBox(width: AppSpacing.sm),
          SkeletonBox(
            width: trailingWidth,
            height: trailingHeight,
            borderRadius: BorderRadius.circular(AppRadii.xs),
          ),
        ],
      ],
    ),
  );
}

// ---------------------------------------------------------------------------
// Screen-Specific High-Performance Skeleton Layouts
// ---------------------------------------------------------------------------

/// Complete Home screen skeleton.
class HomeScreenSkeleton extends StatelessWidget {
  const HomeScreenSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      physics: const NeverScrollableScrollPhysics(),
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md, vertical: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // Header
          const Row(
            children: [
              SkeletonCircle(size: 38),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 150, height: 18),
                    SizedBox(height: 6),
                    SkeletonLine(width: 100, height: 12),
                  ],
                ),
              ),
              SkeletonCircle(size: 34),
            ],
          ),
          const SizedBox(height: AppSpacing.lg),
          // Munim hero
          SkeletonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                SkeletonPill(width: 90, height: 24),
                SizedBox(height: AppSpacing.md),
                SkeletonLine(height: 22),
                SizedBox(height: 8),
                SkeletonLine(width: 220, height: 18),
                SizedBox(height: AppSpacing.md),
                SkeletonBox(width: 130, height: 36),
              ],
            ),
          ),
          const SizedBox(height: AppSpacing.xl),
          const SkeletonLine(width: 140, height: 18),
          const SizedBox(height: AppSpacing.sm),
          // Metric grid
          Row(
            children: const [
              Expanded(
                child: SkeletonCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SkeletonLine(width: 50, height: 24),
                      SizedBox(height: 8),
                      SkeletonLine(width: 80, height: 12),
                    ],
                  ),
                ),
              ),
              SizedBox(width: 12),
              Expanded(
                child: SkeletonCard(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      SkeletonLine(width: 50, height: 24),
                      SizedBox(height: 8),
                      SkeletonLine(width: 80, height: 12),
                    ],
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
          const SkeletonLine(width: 120, height: 18),
          const SizedBox(height: AppSpacing.sm),
          // Quick actions
          Wrap(
            spacing: 8,
            runSpacing: 8,
            children: const [
              SkeletonPill(width: 90, height: 36),
              SkeletonPill(width: 130, height: 36),
              SkeletonPill(width: 95, height: 36),
              SkeletonPill(width: 85, height: 36),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
          const SkeletonLine(width: 130, height: 18),
          const SizedBox(height: AppSpacing.sm),
          const SkeletonTile(),
          const SkeletonTile(),
          const SkeletonTile(),
        ],
      ),
    ),
  );
}

/// Home metric grid skeleton.
class HomeMetricGridSkeleton extends StatelessWidget {
  const HomeMetricGridSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: Row(
        children: const [
          Expanded(
            child: SkeletonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SkeletonLine(width: 54, height: 26),
                  SizedBox(height: 8),
                  SkeletonLine(width: 80, height: 12),
                ],
              ),
            ),
          ),
          SizedBox(width: 12),
          Expanded(
            child: SkeletonCard(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SkeletonLine(width: 48, height: 26),
                  SizedBox(height: 8),
                  SkeletonLine(width: 86, height: 12),
                ],
              ),
            ),
          ),
        ],
      ),
    ),
  );
}

/// Generic list skeleton with customizable rows.
class ListSkeleton extends StatelessWidget {
  const ListSkeleton({
    super.key,
    this.rows = 6,
    this.circular = true,
    this.leadingSize = 42,
  });

  final int rows;
  final bool circular;
  final double leadingSize;

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.md),
      child: Column(
        children: List<Widget>.generate(
          rows,
          (index) => Column(
            children: [
              SkeletonTile(
                leadingSize: leadingSize,
                circular: circular,
              ),
              if (index < rows - 1)
                const Divider(indent: 56, height: 1),
            ],
          ),
        ),
      ),
    ),
  );
}

/// Inventory item detail skeleton.
class InventoryDetailSkeleton extends StatelessWidget {
  const InventoryDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 160, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 100, height: 14),
                  ],
                ),
              ),
            ],
          ),
          const SizedBox(height: AppSpacing.xl),
          const SkeletonLine(width: 100, height: 38),
          const SizedBox(height: 8),
          const SkeletonLine(width: 120, height: 14),
          const SizedBox(height: AppSpacing.lg),
          const Divider(),
          const SizedBox(height: AppSpacing.md),
          const _SkeletonDetailRow(),
          const SizedBox(height: AppSpacing.md),
          const _SkeletonDetailRow(),
          const SizedBox(height: AppSpacing.md),
          const _SkeletonDetailRow(),
          const SizedBox(height: AppSpacing.xl),
          const SkeletonBox(width: double.infinity, height: 52),
          const SizedBox(height: AppSpacing.md),
          const SkeletonLine(height: 12),
          const SizedBox(height: 6),
          const SkeletonLine(width: 240, height: 12),
        ],
      ),
    ),
  );
}

/// Order detail skeleton.
class OrderDetailSkeleton extends StatelessWidget {
  const OrderDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 140, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 180, height: 12),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonPill(width: 100, height: 28),
          SizedBox(height: AppSpacing.md),
          SkeletonLine(width: 140, height: 32),
          SizedBox(height: 6),
          SkeletonLine(width: 90, height: 14),
          SizedBox(height: AppSpacing.xl),
          Divider(),
          SizedBox(height: AppSpacing.lg),
          SkeletonLine(width: 110, height: 20),
          SizedBox(height: AppSpacing.md),
          _TimelineSkeleton(),
          SizedBox(height: AppSpacing.lg),
          SkeletonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonLine(width: 130, height: 14),
                SizedBox(height: 8),
                SkeletonLine(width: 200, height: 16),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

/// Approval detail skeleton.
class ApprovalDetailSkeleton extends StatelessWidget {
  const ApprovalDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 160, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 200, height: 12),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonPill(width: 90, height: 26),
          SizedBox(height: AppSpacing.lg),
          SkeletonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonLine(width: 150, height: 20),
                SizedBox(height: 10),
                _SkeletonDetailRow(),
                SizedBox(height: 8),
                _SkeletonDetailRow(),
                SizedBox(height: 8),
                _SkeletonDetailRow(),
              ],
            ),
          ),
          SizedBox(height: AppSpacing.lg),
          Divider(),
          SizedBox(height: AppSpacing.md),
          SkeletonLine(width: 120, height: 18),
          SizedBox(height: AppSpacing.md),
          _TimelineSkeleton(),
          SizedBox(height: AppSpacing.xl),
          SkeletonBox(width: double.infinity, height: 50),
          SizedBox(height: AppSpacing.sm),
          SkeletonBox(width: double.infinity, height: 50),
        ],
      ),
    ),
  );
}

/// Recommendation detail skeleton.
class RecommendationDetailSkeleton extends StatelessWidget {
  const RecommendationDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 150, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 120, height: 14),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonPill(width: 120, height: 26),
          SizedBox(height: AppSpacing.md),
          SkeletonLine(width: 220, height: 28),
          SizedBox(height: AppSpacing.xs),
          SkeletonLine(width: 160, height: 16),
          SizedBox(height: AppSpacing.xl),
          Divider(),
          SizedBox(height: AppSpacing.md),
          _SkeletonDetailRow(),
          SizedBox(height: AppSpacing.md),
          _SkeletonDetailRow(),
          SizedBox(height: AppSpacing.md),
          _SkeletonDetailRow(),
          SizedBox(height: AppSpacing.xl),
          SkeletonLine(height: 14),
          SizedBox(height: 6),
          SkeletonLine(width: 250, height: 14),
        ],
      ),
    ),
  );
}

/// Analytics screen skeleton.
class AnalyticsScreenSkeleton extends StatelessWidget {
  const AnalyticsScreenSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 160, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 200, height: 13),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonLine(width: 120, height: 36),
          SizedBox(height: 6),
          SkeletonLine(width: 190, height: 14),
          SizedBox(height: AppSpacing.xl),
          SkeletonLine(width: 140, height: 18),
          SizedBox(height: AppSpacing.md),
          SkeletonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonLine(width: 60, height: 26),
                SizedBox(height: 8),
                SkeletonLine(width: 180, height: 14),
              ],
            ),
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonTile(),
          SkeletonTile(),
          SkeletonTile(),
          SizedBox(height: AppSpacing.md),
          SkeletonCard(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                SkeletonLine(width: 60, height: 26),
                SizedBox(height: 8),
                SkeletonLine(width: 160, height: 14),
              ],
            ),
          ),
        ],
      ),
    ),
  );
}

/// Analytics detail screen skeleton.
class AnalyticsDetailSkeleton extends StatelessWidget {
  const AnalyticsDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: List.generate(
          5,
          (index) => Padding(
            padding: const EdgeInsets.symmetric(vertical: AppSpacing.sm),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: const [
                Row(
                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                  children: [
                    SkeletonLine(width: 140, height: 14),
                    SkeletonLine(width: 60, height: 14),
                  ],
                ),
                SizedBox(height: AppSpacing.xs),
                SkeletonBox(width: double.infinity, height: 8),
              ],
            ),
          ),
        ),
      ),
    ),
  );
}

/// Negotiation detail skeleton.
class NegotiationDetailSkeleton extends StatelessWidget {
  const NegotiationDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 160, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 180, height: 12),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonLine(width: 200, height: 28),
          SizedBox(height: 6),
          SkeletonLine(width: 130, height: 14),
          SizedBox(height: AppSpacing.md),
          SkeletonPill(width: 80, height: 26),
          SizedBox(height: AppSpacing.xl),
          _TimelineSkeleton(),
        ],
      ),
    ),
  );
}

/// Supplier detail skeleton.
class SupplierDetailSkeleton extends StatelessWidget {
  const SupplierDetailSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 150, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 180, height: 12),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonLine(width: 220, height: 28),
          SizedBox(height: 8),
          SkeletonPill(width: 80, height: 26),
          SizedBox(height: AppSpacing.xl),
          SkeletonLine(width: 140, height: 18),
          SizedBox(height: AppSpacing.sm),
          SkeletonTile(circular: false),
          SkeletonTile(circular: false),
          SkeletonTile(circular: false),
        ],
      ),
    ),
  );
}

/// Profile screen skeleton.
class ProfileScreenSkeleton extends StatelessWidget {
  const ProfileScreenSkeleton({super.key});

  @override
  Widget build(BuildContext context) => VyaparShimmer(
    child: SingleChildScrollView(
      padding: const EdgeInsets.all(AppSpacing.md),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: const [
          Row(
            children: [
              SkeletonCircle(size: 36),
              SizedBox(width: AppSpacing.sm),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    SkeletonLine(width: 150, height: 20),
                    SizedBox(height: 6),
                    SkeletonLine(width: 180, height: 12),
                  ],
                ),
              ),
            ],
          ),
          SizedBox(height: AppSpacing.lg),
          SkeletonLine(width: 240, height: 30),
          SizedBox(height: 8),
          SkeletonLine(width: 180, height: 14),
          SizedBox(height: AppSpacing.xl),
          SkeletonLine(width: 80, height: 18),
          SizedBox(height: AppSpacing.sm),
          SkeletonTile(),
          SkeletonTile(),
        ],
      ),
    ),
  );
}

/// A2A conversation skeleton.
class A2AConversationSkeleton extends StatelessWidget {
  const A2AConversationSkeleton({super.key});

  @override
  Widget build(BuildContext context) => const VyaparShimmer(
    child: Padding(
      padding: EdgeInsets.all(AppSpacing.md),
      child: _TimelineSkeleton(items: 4),
    ),
  );
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

class _SkeletonDetailRow extends StatelessWidget {
  const _SkeletonDetailRow();

  @override
  Widget build(BuildContext context) => const Row(
    mainAxisAlignment: MainAxisAlignment.spaceBetween,
    children: [
      SkeletonLine(width: 110, height: 14),
      SkeletonLine(width: 90, height: 14),
    ],
  );
}

class _TimelineSkeleton extends StatelessWidget {
  const _TimelineSkeleton({this.items = 3});

  final int items;

  @override
  Widget build(BuildContext context) => Column(
    children: List.generate(
      items,
      (index) => Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Column(
              children: [
                const SkeletonCircle(size: 16),
                if (index < items - 1)
                  Container(
                    width: 2,
                    height: 36,
                    color: AppColors.outline.withValues(alpha: 0.6),
                  ),
              ],
            ),
            const SizedBox(width: AppSpacing.md),
            const Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  SkeletonLine(width: 140, height: 14),
                  SizedBox(height: 6),
                  SkeletonLine(width: 90, height: 11),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}
