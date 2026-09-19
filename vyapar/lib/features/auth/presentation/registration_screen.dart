import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:vyapar/design_system/components/app_button.dart';
import 'package:vyapar/design_system/components/app_header.dart';
import 'package:vyapar/design_system/components/app_text_field.dart';
import 'package:vyapar/design_system/components/states.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/layout/adaptive_padding.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';
import 'package:vyapar/design_system/tokens/spacing.dart';
import 'package:vyapar/features/auth/providers/auth_provider.dart';

class RegistrationScreen extends StatelessWidget {
  const RegistrationScreen({this.initialRole, super.key});

  final String? initialRole;

  @override
  Widget build(BuildContext context) {
    if (initialRole == 'supplier') {
      return const SupplierRegistrationScreen();
    }
    return const MerchantRegistrationScreen();
  }
}

class MerchantRegistrationScreen extends ConsumerStatefulWidget {
  const MerchantRegistrationScreen({super.key});

  @override
  ConsumerState<MerchantRegistrationScreen> createState() =>
      _MerchantRegistrationScreenState();
}

class _MerchantRegistrationScreenState
    extends ConsumerState<MerchantRegistrationScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _business = TextEditingController();
  final _store = TextEditingController();
  final _password = TextEditingController();
  final _gstin = TextEditingController();
  final _pan = TextEditingController();
  final _addressLine = TextEditingController(text: 'Shop 14, Main Market Road');
  final _city = TextEditingController(text: 'Bengaluru');
  final _state = TextEditingController(text: 'Karnataka');
  final _pincode = TextEditingController(text: '560038');

  @override
  void initState() {
    super.initState();
    _email.text = ref.read(pendingRegistrationProvider)?.email ?? '';
  }

  @override
  void dispose() {
    _email.dispose();
    _business.dispose();
    _store.dispose();
    _password.dispose();
    _gstin.dispose();
    _pan.dispose();
    _addressLine.dispose();
    _city.dispose();
    _state.dispose();
    _pincode.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    await ref
        .read(registrationControllerProvider.notifier)
        .register(
          email: _email.text,
          businessName: _business.text,
          storeName: _store.text,
          password: _password.text,
          role: 'merchant',
          gstin: _gstin.text.trim().isNotEmpty
              ? _gstin.text.trim().toUpperCase()
              : null,
          pan: _pan.text.trim().isNotEmpty
              ? _pan.text.trim().toUpperCase()
              : null,
          address: {
            'address_line1': _addressLine.text.trim(),
            'city': _city.text.trim(),
            'state': _state.text.trim(),
            'pincode': _pincode.text.trim(),
            'country': 'India',
          },
        );
  }

  @override
  Widget build(BuildContext context) {
    final pending = ref.watch(pendingRegistrationProvider);
    final registration = ref.watch(registrationControllerProvider);
    final theme = Theme.of(context);

    if (pending == null) {
      return Scaffold(
        body: SafeArea(
          child: EmptyState(
            title: 'Verification required',
            message:
                'Verify a phone number or identity before creating a merchant business.',
            actionLabel: 'Start verification',
            onAction: () => context.go('/otp?registration=true&role=merchant'),
          ),
        ),
      );
    }

    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Merchant Registration',
                  subtitle: 'Set up your Kirana store & smart replenishments',
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: () =>
                        context.canPop() ? context.pop() : context.go('/sign-in'),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Form(
                  key: _form,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: AppColors.paleBlue,
                          borderRadius: BorderRadius.circular(AppRadii.md),
                          border: Border.all(
                            color: AppColors.blue.withValues(alpha: 0.2),
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius:
                                    BorderRadius.circular(AppRadii.sm),
                              ),
                              child: const VyaparIcon(
                                VyaparIcons.store,
                                size: 24,
                                color: AppColors.navy,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'Retail Merchant Account',
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(fontWeight: FontWeight.bold),
                                  ),
                                  Text(
                                    'Manage stock, get supplier price quotes, and use Munim AI.',
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color: AppColors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      AppTextField(
                        fieldKey: const ValueKey('registration_email'),
                        controller: _email,
                        label: 'Email address',
                        enabled: pending.email == null,
                        keyboardType: TextInputType.emailAddress,
                        prefixIcon: VyaparIcons.email,
                        validator: (value) => (value?.contains('@') ?? false)
                            ? null
                            : 'Enter a valid email address',
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_business'),
                        controller: _business,
                        label: 'Kirana / Business Name',
                        hint: 'e.g. Sharma Provision Store',
                        prefixIcon: VyaparIcons.store,
                        validator: (value) => (value?.isEmpty ?? true)
                            ? 'Enter your business name'
                            : null,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_store'),
                        controller: _store,
                        label: 'Store Outlet Name',
                        hint: 'e.g. Indiranagar Main Branch',
                        prefixIcon: VyaparIcons.location,
                        validator: (value) => (value?.isEmpty ?? true)
                            ? 'Enter store outlet name'
                            : null,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_password'),
                        controller: _password,
                        label: 'Account Password',
                        hint: 'Min 12 chars (upper, lower, number)',
                        obscureText: true,
                        prefixIcon: VyaparIcons.password,
                        validator: (value) {
                          if (value == null || value.length < 12) {
                            return 'Must be at least 12 characters';
                          }
                          final hasUpper = value.contains(RegExp(r'[A-Z]'));
                          final hasLower = value.contains(RegExp(r'[a-z]'));
                          final hasDigit = value.contains(RegExp(r'[0-9]'));
                          if (!hasUpper || !hasLower || !hasDigit) {
                            return 'Must contain uppercase, lowercase & number';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Row(
                        children: [
                          Expanded(
                            child: AppTextField(
                              controller: _gstin,
                              label: 'GSTIN (Optional)',
                              hint: '29ABCDE1234F1Z5',
                              prefixIcon: VyaparIcons.invoice,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _pan,
                              label: 'PAN (Optional)',
                              hint: 'ABCDE1234F',
                              prefixIcon: VyaparIcons.wallet,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      Text(
                        'Store Location',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppTextField(
                        controller: _addressLine,
                        label: 'Street Address',
                        hint: 'Shop 14, Main Road',
                        prefixIcon: VyaparIcons.location,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: [
                          Expanded(
                            child: AppTextField(
                              controller: _city,
                              label: 'City',
                              hint: 'Bengaluru',
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _state,
                              label: 'State',
                              hint: 'Karnataka',
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _pincode,
                              label: 'PIN Code',
                              hint: '560038',
                              keyboardType: TextInputType.number,
                            ),
                          ),
                        ],
                      ),
                      if (registration.hasError) ...[
                        const SizedBox(height: AppSpacing.md),
                        AppErrorState(error: registration.error!),
                      ],
                      const SizedBox(height: AppSpacing.xl),
                      PrimaryButton(
                        key: const ValueKey('submit_registration_button'),
                        label: 'Register as Merchant',
                        loading: registration.isLoading,
                        leading: const VyaparIcon(
                          VyaparIcons.store,
                          color: Colors.white,
                          size: 18,
                        ),
                        onPressed: _submit,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Center(
                        child: TextButton.icon(
                          icon: const VyaparIcon(
                            VyaparIcons.truck,
                            size: 16,
                            color: AppColors.blue,
                          ),
                          label: const Text(
                            'Are you a wholesale supplier? Register as Supplier',
                            style: TextStyle(color: AppColors.blue),
                          ),
                          onPressed: () => context.go('/register/supplier'),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.lg),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class SupplierRegistrationScreen extends ConsumerStatefulWidget {
  const SupplierRegistrationScreen({super.key});

  @override
  ConsumerState<SupplierRegistrationScreen> createState() =>
      _SupplierRegistrationScreenState();
}

class _SupplierRegistrationScreenState
    extends ConsumerState<SupplierRegistrationScreen> {
  final _form = GlobalKey<FormState>();
  final _email = TextEditingController();
  final _business = TextEditingController();
  final _store = TextEditingController();
  final _password = TextEditingController();
  final _category = TextEditingController(text: 'FMCG Distribution');
  final _gstin = TextEditingController();
  final _pan = TextEditingController();
  final _addressLine =
      TextEditingController(text: 'Plot 42, Industrial Wholesale Area');
  final _city = TextEditingController(text: 'Bengaluru');
  final _state = TextEditingController(text: 'Karnataka');
  final _pincode = TextEditingController(text: '560058');

  static const _categoryPresets = [
    'FMCG Distribution',
    'Beverages & Soft Drinks',
    'Dairy & Bakery',
    'Grains & Staples',
    'Personal Care',
  ];

  @override
  void initState() {
    super.initState();
    _email.text = ref.read(pendingRegistrationProvider)?.email ?? '';
  }

  @override
  void dispose() {
    _email.dispose();
    _business.dispose();
    _store.dispose();
    _password.dispose();
    _category.dispose();
    _gstin.dispose();
    _pan.dispose();
    _addressLine.dispose();
    _city.dispose();
    _state.dispose();
    _pincode.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    if (!(_form.currentState?.validate() ?? false)) return;
    await ref
        .read(registrationControllerProvider.notifier)
        .register(
          email: _email.text,
          businessName: _business.text,
          storeName: _store.text,
          password: _password.text,
          role: 'supplier',
          category: _category.text.trim(),
          gstin: _gstin.text.trim().isNotEmpty
              ? _gstin.text.trim().toUpperCase()
              : null,
          pan: _pan.text.trim().isNotEmpty
              ? _pan.text.trim().toUpperCase()
              : null,
          address: {
            'address_line1': _addressLine.text.trim(),
            'city': _city.text.trim(),
            'state': _state.text.trim(),
            'pincode': _pincode.text.trim(),
            'category': _category.text.trim(),
            'country': 'India',
          },
        );
  }

  @override
  Widget build(BuildContext context) {
    final pending = ref.watch(pendingRegistrationProvider);
    final registration = ref.watch(registrationControllerProvider);
    final theme = Theme.of(context);

    if (pending == null) {
      return Scaffold(
        body: SafeArea(
          child: EmptyState(
            title: 'Verification required',
            message:
                'Verify a phone number or identity before registering as a wholesale supplier.',
            actionLabel: 'Start verification',
            onAction: () => context.go('/otp?registration=true&role=supplier'),
          ),
        ),
      );
    }

    return Scaffold(
      body: SafeArea(
        child: CustomScrollView(
          slivers: [
            SliverPadding(
              padding: const EdgeInsets.all(AppSpacing.md),
              sliver: SliverToBoxAdapter(
                child: AppHeader(
                  title: 'Supplier Registration',
                  subtitle:
                      'Connect wholesale inventory to Paytm ONE Vyapar A2A network',
                  leading: IconAction(
                    icon: VyaparIcons.back,
                    label: 'Back',
                    onPressed: () =>
                        context.canPop() ? context.pop() : context.go('/sign-in'),
                  ),
                ),
              ),
            ),
            SliverToBoxAdapter(
              child: AdaptivePadding(
                child: Form(
                  key: _form,
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Container(
                        padding: const EdgeInsets.all(AppSpacing.md),
                        decoration: BoxDecoration(
                          color: const Color(0xFFE8F5E9),
                          borderRadius: BorderRadius.circular(AppRadii.md),
                          border: Border.all(
                            color:
                                AppColors.success.withValues(alpha: 0.3),
                          ),
                        ),
                        child: Row(
                          children: [
                            Container(
                              padding: const EdgeInsets.all(8),
                              decoration: BoxDecoration(
                                color: Colors.white,
                                borderRadius:
                                    BorderRadius.circular(AppRadii.sm),
                              ),
                              child: const VyaparIcon(
                                VyaparIcons.truck,
                                size: 24,
                                color: AppColors.success,
                              ),
                            ),
                            const SizedBox(width: AppSpacing.sm),
                            Expanded(
                              child: Column(
                                crossAxisAlignment: CrossAxisAlignment.start,
                                children: [
                                  Text(
                                    'B2B Wholesale Distributor',
                                    style: theme.textTheme.titleMedium
                                        ?.copyWith(fontWeight: FontWeight.bold),
                                  ),
                                  Text(
                                    'Receive automated buyer RFQs, negotiate with AI agents, and supply local stores.',
                                    style: theme.textTheme.bodySmall?.copyWith(
                                      color: AppColors.muted,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                          ],
                        ),
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      AppTextField(
                        fieldKey: const ValueKey('registration_email'),
                        controller: _email,
                        label: 'Official Email address',
                        enabled: pending.email == null,
                        keyboardType: TextInputType.emailAddress,
                        prefixIcon: VyaparIcons.email,
                        validator: (value) => (value?.contains('@') ?? false)
                            ? null
                            : 'Enter a valid email address',
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_business'),
                        controller: _business,
                        label: 'Distributor / Enterprise Name',
                        hint: 'e.g. Metro Cash & Carry Hub',
                        prefixIcon: VyaparIcons.truck,
                        validator: (value) => (value?.isEmpty ?? true)
                            ? 'Enter your distributor / enterprise name'
                            : null,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_store'),
                        controller: _store,
                        label: 'Fulfillment Center / Warehouse Name',
                        hint: 'e.g. Central Bengaluru Distribution Center',
                        prefixIcon: VyaparIcons.location,
                        validator: (value) => (value?.isEmpty ?? true)
                            ? 'Enter warehouse / hub name'
                            : null,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Text(
                        'Wholesale Supply Category',
                        style: theme.textTheme.labelMedium?.copyWith(
                          color: AppColors.muted,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.xs),
                      Wrap(
                        spacing: 8,
                        runSpacing: 8,
                        children: [
                          for (final cat in _categoryPresets)
                            ActionChip(
                              label: Text(cat),
                              backgroundColor: _category.text == cat
                                  ? AppColors.paleBlue
                                  : AppColors.surface,
                              side: BorderSide(
                                color: _category.text == cat
                                    ? AppColors.blue
                                    : AppColors.outline,
                              ),
                              onPressed: () =>
                                  setState(() => _category.text = cat),
                            ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppTextField(
                        controller: _category,
                        label: 'Category Details',
                        hint: 'e.g. FMCG Distribution',
                        prefixIcon: VyaparIcons.tag,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      AppTextField(
                        fieldKey: const ValueKey('registration_password'),
                        controller: _password,
                        label: 'Account Password',
                        hint: 'Min 12 chars (upper, lower, number)',
                        obscureText: true,
                        prefixIcon: VyaparIcons.password,
                        validator: (value) {
                          if (value == null || value.length < 12) {
                            return 'Must be at least 12 characters';
                          }
                          final hasUpper = value.contains(RegExp(r'[A-Z]'));
                          final hasLower = value.contains(RegExp(r'[a-z]'));
                          final hasDigit = value.contains(RegExp(r'[0-9]'));
                          if (!hasUpper || !hasLower || !hasDigit) {
                            return 'Must contain uppercase, lowercase & number';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Row(
                        children: [
                          Expanded(
                            child: AppTextField(
                              controller: _gstin,
                              label: 'GSTIN (Tax Invoicing)',
                              hint: '29ABCDE1234F1Z5',
                              prefixIcon: VyaparIcons.invoice,
                              validator: (v) =>
                                  v == null || v.trim().isEmpty
                                      ? 'GSTIN is required for wholesale distributors'
                                      : null,
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _pan,
                              label: 'Entity PAN',
                              hint: 'ABCDE1234F',
                              prefixIcon: VyaparIcons.wallet,
                            ),
                          ),
                        ],
                      ),
                      const SizedBox(height: AppSpacing.lg),
                      Text(
                        'Dispatch & Warehouse Location',
                        style: theme.textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      AppTextField(
                        controller: _addressLine,
                        label: 'Warehouse Address',
                        hint: 'Plot 42, Industrial Wholesale Area',
                        prefixIcon: VyaparIcons.location,
                      ),
                      const SizedBox(height: AppSpacing.sm),
                      Row(
                        children: [
                          Expanded(
                            child: AppTextField(
                              controller: _city,
                              label: 'City',
                              hint: 'Bengaluru',
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _state,
                              label: 'State',
                              hint: 'Karnataka',
                            ),
                          ),
                          const SizedBox(width: AppSpacing.sm),
                          Expanded(
                            child: AppTextField(
                              controller: _pincode,
                              label: 'PIN Code',
                              hint: '560058',
                              keyboardType: TextInputType.number,
                            ),
                          ),
                        ],
                      ),
                      if (registration.hasError) ...[
                        const SizedBox(height: AppSpacing.md),
                        AppErrorState(error: registration.error!),
                      ],
                      const SizedBox(height: AppSpacing.xl),
                      PrimaryButton(
                        key: const ValueKey(
                          'submit_supplier_registration_button',
                        ),
                        label: 'Register as B2B Supplier',
                        loading: registration.isLoading,
                        leading: const VyaparIcon(
                          VyaparIcons.truck,
                          color: Colors.white,
                          size: 18,
                        ),
                        onPressed: _submit,
                      ),
                      const SizedBox(height: AppSpacing.md),
                      Center(
                        child: TextButton.icon(
                          icon: const VyaparIcon(
                            VyaparIcons.store,
                            size: 16,
                            color: AppColors.navy,
                          ),
                          label: const Text(
                            'Are you a retail shopkeeper? Register as Merchant',
                            style: TextStyle(color: AppColors.navy),
                          ),
                          onPressed: () => context.go('/register/merchant'),
                        ),
                      ),
                      const SizedBox(height: AppSpacing.lg),
                    ],
                  ),
                ),
              ),
            ),
          ],
        ),
      ),
    );
  }
}
