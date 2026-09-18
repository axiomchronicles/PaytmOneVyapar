import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/design_system/components/shimmer.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';

Widget _wrap(Widget child) => MaterialApp(
  theme: AppTheme.light,
  home: Scaffold(body: child),
);

void main() {
  group('VyaparShimmer & Skeleton Primitives', () {
    testWidgets('renders VyaparShimmer with primitive blocks', (tester) async {
      await tester.pumpWidget(
        _wrap(
          const VyaparShimmer(
            child: Column(
              children: [
                SkeletonBox(width: 100, height: 20),
                SkeletonLine(width: 150, height: 14),
                SkeletonCircle(size: 40),
                SkeletonPill(width: 60, height: 24),
                SkeletonCard(child: Text('Card Content')),
                SkeletonTile(),
              ],
            ),
          ),
        ),
      );

      // Verify that the widgets are present in the tree
      expect(find.byType(VyaparShimmer), findsOneWidget);
      expect(find.byType(SkeletonBox), findsWidgets);
      expect(find.byType(SkeletonLine), findsWidgets);
      expect(find.byType(SkeletonCircle), findsWidgets);
      expect(find.byType(SkeletonPill), findsWidgets);
      expect(find.byType(SkeletonCard), findsWidgets);
      expect(find.byType(SkeletonTile), findsWidgets);

      // Advance time to verify smooth ticker animation
      await tester.pump(const Duration(milliseconds: 500));
      await tester.pump(const Duration(milliseconds: 1000));
    });

    testWidgets('respects disabled state in VyaparShimmer', (tester) async {
      await tester.pumpWidget(
        _wrap(
          const VyaparShimmer(
            enabled: false,
            child: SkeletonLine(width: 80, height: 16),
          ),
        ),
      );

      expect(find.byType(ShaderMask), findsNothing);
      expect(find.byType(SkeletonLine), findsOneWidget);
    });
  });

  group('Screen-Specific Skeletons', () {
    testWidgets('HomeScreenSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const HomeScreenSkeleton()));
      expect(find.byType(HomeScreenSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('HomeMetricGridSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const HomeMetricGridSkeleton()));
      expect(find.byType(HomeMetricGridSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('InventoryDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const InventoryDetailSkeleton()));
      expect(find.byType(InventoryDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('OrderDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const OrderDetailSkeleton()));
      expect(find.byType(OrderDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('ApprovalDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const ApprovalDetailSkeleton()));
      expect(find.byType(ApprovalDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('RecommendationDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const RecommendationDetailSkeleton()));
      expect(find.byType(RecommendationDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('AnalyticsScreenSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const AnalyticsScreenSkeleton()));
      expect(find.byType(AnalyticsScreenSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('AnalyticsDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const AnalyticsDetailSkeleton()));
      expect(find.byType(AnalyticsDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('NegotiationDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const NegotiationDetailSkeleton()));
      expect(find.byType(NegotiationDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('SupplierDetailSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const SupplierDetailSkeleton()));
      expect(find.byType(SupplierDetailSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('ProfileScreenSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const ProfileScreenSkeleton()));
      expect(find.byType(ProfileScreenSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });

    testWidgets('A2AConversationSkeleton renders without error', (tester) async {
      await tester.pumpWidget(_wrap(const A2AConversationSkeleton()));
      expect(find.byType(A2AConversationSkeleton), findsOneWidget);
      await tester.pump(const Duration(milliseconds: 300));
    });
  });
}
