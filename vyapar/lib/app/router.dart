import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/app/app_shell.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/features/activity/presentation/activity_screen.dart';
import 'package:vyapar/features/analytics/models/analytics_detail.dart';
import 'package:vyapar/features/analytics/presentation/analytics_detail_screen.dart';
import 'package:vyapar/features/analytics/presentation/analytics_screen.dart';
import 'package:vyapar/features/approvals/presentation/approval_detail_screen.dart';
import 'package:vyapar/features/approvals/presentation/approvals_screen.dart';
import 'package:vyapar/features/auth/presentation/otp_screen.dart';
import 'package:vyapar/features/auth/presentation/registration_screen.dart';
import 'package:vyapar/features/auth/presentation/session_recovery_screen.dart';
import 'package:vyapar/features/auth/presentation/sign_in_screen.dart';
import 'package:vyapar/features/auth/presentation/splash_screen.dart';
import 'package:vyapar/features/auth/presentation/welcome_screen.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';
import 'package:vyapar/features/home/presentation/home_screen.dart';
import 'package:vyapar/features/inventory/presentation/inventory_detail_screen.dart';
import 'package:vyapar/features/inventory/presentation/inventory_screen.dart';
import 'package:vyapar/features/munim/presentation/munim_screen.dart';
import 'package:vyapar/features/negotiations/presentation/negotiation_detail_screen.dart';
import 'package:vyapar/features/negotiations/presentation/negotiations_screen.dart';
import 'package:vyapar/features/notifications/presentation/notifications_screen.dart';
import 'package:vyapar/features/orders/presentation/order_detail_screen.dart';
import 'package:vyapar/features/orders/presentation/orders_screen.dart';
import 'package:vyapar/features/profile/presentation/profile_screen.dart';
import 'package:vyapar/features/recommendations/presentation/recommendation_detail_screen.dart';
import 'package:vyapar/features/recommendations/presentation/recommendations_screen.dart';
import 'package:vyapar/features/settings/presentation/capabilities_screen.dart';
import 'package:vyapar/features/settings/presentation/language_screen.dart';
import 'package:vyapar/features/settings/presentation/more_screen.dart';
import 'package:vyapar/features/settings/presentation/settings_screen.dart';
import 'package:vyapar/features/suppliers/presentation/supplier_detail_screen.dart';
import 'package:vyapar/features/suppliers/presentation/suppliers_screen.dart';
import 'package:vyapar/features/voice/presentation/voice_screen.dart';

final appRouterProvider = Provider<GoRouter>((ref) {
  final auth = ref.watch(authControllerProvider);
  return GoRouter(
    initialLocation: '/splash',
    redirect: (context, state) {
      final location = state.matchedLocation;
      if (auth.isLoading) return location == '/splash' ? null : '/splash';
      if (auth.hasError) {
        return location == '/session-recovery' ? null : '/session-recovery';
      }
      final authenticated = auth.value?.isAuthenticated ?? false;
      final publicRoute =
          location == '/welcome' ||
          location == '/sign-in' ||
          location == '/otp' ||
          location == '/register' ||
          location == '/language';
      if (!authenticated) {
        return publicRoute
            ? null
            : Uri(
                path: '/welcome',
                queryParameters: {'redirect': state.uri.toString()},
              ).toString();
      }
      if (location == '/splash' ||
          location == '/welcome' ||
          location == '/sign-in') {
        final intended = state.uri.queryParameters['redirect'];
        return intended != null &&
                intended.startsWith('/') &&
                !intended.startsWith('//') &&
                !intended.startsWith('/welcome') &&
                !intended.startsWith('/sign-in')
            ? intended
            : '/home';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/splash',
        builder: (context, state) => const SplashScreen(),
      ),
      GoRoute(
        path: '/welcome',
        builder: (context, state) =>
            WelcomeScreen(redirect: state.uri.queryParameters['redirect']),
      ),
      GoRoute(
        path: '/sign-in',
        builder: (context, state) =>
            SignInScreen(redirect: state.uri.queryParameters['redirect']),
      ),
      GoRoute(
        path: '/otp',
        builder: (context, state) => OtpScreen(
          registration: state.uri.queryParameters['registration'] == 'true',
        ),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegistrationScreen(),
      ),
      GoRoute(
        path: '/language',
        builder: (context, state) => const LanguageScreen(),
      ),
      GoRoute(
        path: '/session-recovery',
        builder: (context, state) => const SessionRecoveryScreen(),
      ),
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            AppShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/home',
                builder: (context, state) => const HomeScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/inventory',
                builder: (context, state) => const InventoryScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/munim',
                builder: (context, state) => const MunimScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/orders',
                builder: (context, state) => const OrdersScreen(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: '/more',
                builder: (context, state) => const MoreScreen(),
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/inventory/:inventoryId',
        builder: (context, state) => InventoryDetailScreen(
          inventoryId: state.pathParameters['inventoryId']!,
        ),
      ),
      GoRoute(
        path: '/recommendations',
        builder: (context, state) => const RecommendationsScreen(),
      ),
      GoRoute(
        path: '/recommendations/:sku',
        builder: (context, state) =>
            RecommendationDetailScreen(sku: state.pathParameters['sku']!),
      ),
      GoRoute(
        path: '/approval/:approvalId',
        builder: (context, state) => ApprovalDetailScreen(
          approvalId: state.pathParameters['approvalId']!,
        ),
      ),
      GoRoute(
        path: '/approvals',
        builder: (context, state) => const ApprovalsScreen(),
      ),
      GoRoute(
        path: '/order/:orderId',
        builder: (context, state) =>
            OrderDetailScreen(orderId: state.pathParameters['orderId']!),
      ),
      GoRoute(
        path: '/voice',
        builder: (context, state) => VoiceScreen(
          approvalId: state.uri.queryParameters['approvalId'],
          proposalId: state.uri.queryParameters['proposalId'],
        ),
      ),
      GoRoute(
        path: '/analytics',
        builder: (context, state) => const AnalyticsScreen(),
      ),
      GoRoute(
        path: '/analytics/:metric',
        builder: (context, state) => AnalyticsDetailScreen(
          metric: AnalyticsMetric.values.byName(
            state.pathParameters['metric']!,
          ),
        ),
      ),
      GoRoute(
        path: '/suppliers',
        builder: (context, state) => const SuppliersScreen(),
      ),
      GoRoute(
        path: '/suppliers/:supplierId',
        builder: (context, state) => SupplierDetailScreen(
          supplierId: state.pathParameters['supplierId']!,
        ),
      ),
      GoRoute(
        path: '/negotiations',
        builder: (context, state) => const NegotiationsScreen(),
      ),
      GoRoute(
        path: '/negotiations/:negotiationId',
        builder: (context, state) => NegotiationDetailScreen(
          negotiationId: state.pathParameters['negotiationId']!,
        ),
      ),
      GoRoute(
        path: '/a2a-activity',
        builder: (context, state) => const ActivityScreen(a2a: true),
      ),
      GoRoute(
        path: '/a2a-activity/:correlationId',
        builder: (context, state) => A2AConversationScreen(
          correlationId: state.pathParameters['correlationId']!,
        ),
      ),
      GoRoute(
        path: '/history',
        builder: (context, state) => const ActivityScreen(a2a: false),
      ),
      GoRoute(
        path: '/notifications',
        builder: (context, state) => const NotificationsScreen(),
      ),
      GoRoute(
        path: '/more/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/more/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/more/capabilities',
        builder: (context, state) => const CapabilitiesScreen(),
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: SafeArea(
        child: Column(
          children: [
            Expanded(
              child: EmptyState(
                title: 'Page not found',
                message: state.uri.path,
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: PrimaryButton(
                label: 'Go home',
                onPressed: () => context.go('/home'),
              ),
            ),
          ],
        ),
      ),
    ),
  );
});
