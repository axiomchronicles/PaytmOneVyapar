import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:vyapar/design_system/icons/vyapar_icons.dart';
import 'package:vyapar/design_system/tokens/colors.dart';
import 'package:vyapar/design_system/tokens/radii.dart';

class AppTextField extends StatelessWidget {
  const AppTextField({
    required this.controller,
    required this.label,
    super.key,
    this.hint,
    this.keyboardType,
    this.textInputAction,
    this.autofillHints,
    this.obscureText = false,
    this.enabled = true,
    this.prefixIcon,
    this.suffix,
    this.validator,
    this.onSubmitted,
    this.fieldKey,
  });

  final TextEditingController controller;
  final String label;
  final String? hint;
  final TextInputType? keyboardType;
  final TextInputAction? textInputAction;
  final Iterable<String>? autofillHints;
  final bool obscureText;
  final bool enabled;
  final List<List<dynamic>>? prefixIcon;
  final Widget? suffix;
  final FormFieldValidator<String>? validator;
  final ValueChanged<String>? onSubmitted;
  final Key? fieldKey;

  @override
  Widget build(BuildContext context) => TextFormField(
    key: fieldKey,
    controller: controller,
    enabled: enabled,
    keyboardType: keyboardType,
    textInputAction: textInputAction,
    autofillHints: autofillHints,
    obscureText: obscureText,
    validator: validator,
    onFieldSubmitted: onSubmitted,
    decoration: InputDecoration(
      labelText: label,
      hintText: hint,
      prefixIcon: prefixIcon == null
          ? null
          : Center(widthFactor: 1, child: VyaparIcon(prefixIcon!, size: 20)),
      suffixIcon: suffix,
    ),
  );
}

class AppSearchField extends StatelessWidget {
  const AppSearchField({
    required this.controller,
    required this.onChanged,
    super.key,
    this.hint = 'Search',
  });

  final TextEditingController controller;
  final ValueChanged<String> onChanged;
  final String hint;

  @override
  Widget build(BuildContext context) => TextField(
    key: const ValueKey('search_field'),
    controller: controller,
    onChanged: onChanged,
    textInputAction: TextInputAction.search,
    decoration: InputDecoration(
      hintText: hint,
      prefixIcon: Center(
        widthFactor: 1,
        child: VyaparIcon(VyaparIcons.search, size: 20),
      ),
    ),
  );
}

class OtpInput extends StatelessWidget {
  const OtpInput({
    required this.controller,
    required this.onCompleted,
    super.key,
    this.length = 6,
  });

  final TextEditingController controller;
  final ValueChanged<String> onCompleted;
  final int length;

  @override
  Widget build(BuildContext context) => Semantics(
    textField: true,
    label: '$length digit verification code',
    child: TextField(
      key: const ValueKey('otp_input'),
      controller: controller,
      keyboardType: TextInputType.number,
      autofillHints: const [AutofillHints.oneTimeCode],
      inputFormatters: [
        FilteringTextInputFormatter.digitsOnly,
        LengthLimitingTextInputFormatter(length),
      ],
      onChanged: (value) {
        if (value.length == length) onCompleted(value);
      },
      style: Theme.of(
        context,
      ).textTheme.headlineMedium?.copyWith(letterSpacing: 18),
      textAlign: TextAlign.center,
      decoration: InputDecoration(
        counterText: '',
        hintText: List<String>.filled(length, '•').join('  '),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(AppRadii.md),
          borderSide: const BorderSide(color: AppColors.outline),
        ),
      ),
    ),
  );
}
