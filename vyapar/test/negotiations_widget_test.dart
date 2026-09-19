import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:intl/date_symbol_data_local.dart';
import 'package:vyapar/core/networking/cursor_page.dart';
import 'package:vyapar/design_system/theme/app_theme.dart';
import 'package:vyapar/features/activity/models/activity.dart';
import 'package:vyapar/features/activity/presentation/activity_screen.dart';
import 'package:vyapar/features/activity/providers/activity_provider.dart';
import 'package:vyapar/features/negotiations/models/negotiation.dart';
import 'package:vyapar/features/negotiations/presentation/negotiation_detail_screen.dart';
import 'package:vyapar/features/negotiations/presentation/negotiations_screen.dart';
import 'package:vyapar/features/negotiations/providers/negotiation_provider.dart';

final _testNegotiation = NegotiationDetail(
  id: 'neg-100',
  supplierId: 'sup-1',
  supplierName: 'Metro Cash & Carry Hub',
  correlationId: 'corr-100',
  sku: 'COLD-COLA-300',
  status: 'ACCEPTED',
  roundCount: 3,
  proposalId: 'prop-100',
  approvalId: 'approval-100',
  constraints: const {
    'quantity': 50,
    'target_price': 435.0,
    'max_price': 460.0,
  },
  currentQuote: const {
    'unit_price': 441.80,
    'quantity': 50,
    'delivery_days': 1,
  },
  history: const [
    {
      'round': 1,
      'event': 'BUYER_RFQ',
      'unit_price': 435.0,
      'quantity': 50,
      'notes': 'Buyer agent issued initial RFQ',
    },
    {
      'round': 1,
      'event': 'INITIAL_QUOTE',
      'unit_price': 470.0,
      'quantity': 50,
      'notes': 'Supplier initial wholesale quote',
    },
    {
      'round': 2,
      'event': 'COUNTER_OFFER',
      'unit_price': 435.0,
      'quantity': 50,
      'notes': 'Counter offer based on target limit',
    },
    {
      'round': 2,
      'event': 'ACCEPTED',
      'unit_price': 441.80,
      'quantity': 50,
      'notes': 'Supplier accepted negotiated concession',
    },
  ],
  createdAt: DateTime.parse('2026-09-18T10:00:00Z'),
);

class _PopulatedNegotiations extends NegotiationListController {
  @override
  Future<CursorPage<NegotiationDetail>> build() async =>
      CursorPage(items: [_testNegotiation]);
}

Widget _testApp(Widget child) =>
    MaterialApp(theme: AppTheme.light, home: child);

void main() {
  setUpAll(() async {
    await initializeDateFormatting('en_IN');
  });

  testWidgets('NegotiationsScreen renders cards with savings and round count', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          negotiationListProvider.overrideWith(_PopulatedNegotiations.new),
        ],
        child: _testApp(const NegotiationsScreen()),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Metro Cash & Carry Hub'), findsOneWidget);
    expect(find.text('COLD-COLA-300'), findsOneWidget);
    expect(find.text('Accepted'), findsOneWidget);
    expect(find.text('3 rounds'), findsOneWidget);
    expect(find.textContaining('Saved'), findsOneWidget);
    expect(find.text('Start Negotiation'), findsOneWidget);
  });

  testWidgets('NegotiationDetailScreen renders timeline and A2A audit card', (
    tester,
  ) async {
    await tester.pumpWidget(
      ProviderScope(
        overrides: [
          negotiationDetailProvider(
            'neg-100',
          ).overrideWith((ref) async => _testNegotiation),
        ],
        child: _testApp(
          const NegotiationDetailScreen(negotiationId: 'neg-100'),
        ),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.text('Metro Cash & Carry Hub'), findsOneWidget);
    expect(find.text('COLD-COLA-300'), findsOneWidget);
    expect(find.text('Agreed Price'), findsOneWidget);
    expect(find.text('Initial Quote'), findsOneWidget);
    expect(find.text('Unit Savings'), findsOneWidget);
    expect(find.text('Target Limit'), findsOneWidget);
    expect(find.text('Purchase Proposal Ready'), findsOneWidget);
    expect(find.text('Review & Approve Proposal'), findsOneWidget);
    expect(find.text('Round 1 · Buyer Quote Request'), findsOneWidget);
    expect(find.text('Round 1 · Supplier Initial Quote'), findsOneWidget);
    expect(find.text('Round 2 · Agent Counter Offer'), findsOneWidget);
    expect(find.text('Round 2 · Supplier Accepted Quote'), findsOneWidget);
    expect(find.text('vyapaar-a2a-v1 Cryptographic Audit'), findsOneWidget);
    expect(find.text('Inspect A2A Protocol Messages'), findsOneWidget);
  });

  testWidgets(
    'A2AConversationScreen renders protocol banner and cryptographic cards',
    (tester) async {
      final mockMessages = [
        ActivityItem(
          id: 'msg-1',
          title: 'Buyer Quote Request',
          kind: 'PURCHASE_REQUEST',
          subtitle: 'OUTBOUND',
          occurredAt: DateTime.parse('2026-09-18T10:00:00Z'),
          status: 'VERIFIED',
          messageId: '00000000-0000-0000-0000-000000000001',
          payload: const {
            'sku': 'COLD-COLA-300',
            'quantity': 50,
            'target_price': 435.0,
          },
        ),
        ActivityItem(
          id: 'msg-2',
          title: 'Supplier Initial Quote',
          kind: 'QUOTE',
          subtitle: 'INBOUND',
          occurredAt: DateTime.parse('2026-09-18T10:01:00Z'),
          status: 'VERIFIED',
          messageId: '00000000-0000-0000-0000-000000000002',
          payload: const {
            'sku': 'COLD-COLA-300',
            'unit_price': 470.0,
            'quantity': 50,
          },
        ),
      ];

      await tester.pumpWidget(
        ProviderScope(
          overrides: [
            a2aConversationProvider(
              'corr-100',
            ).overrideWith((ref) async => mockMessages),
          ],
          child: _testApp(
            const A2AConversationScreen(correlationId: 'corr-100'),
          ),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('vyapaar-a2a-v1 mutual cryptographic protocol'),
        findsOneWidget,
      );
      expect(find.text('OUTBOUND → Supplier'), findsOneWidget);
      expect(find.text('INBOUND ← Supplier'), findsOneWidget);
      expect(find.text('HMAC Verified'), findsNWidgets(2));
      expect(find.text('PURCHASE_REQUEST'), findsOneWidget);
      expect(find.text('QUOTE'), findsOneWidget);
    },
  );
}
