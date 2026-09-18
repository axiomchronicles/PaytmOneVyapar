import 'package:intl/intl.dart';

final NumberFormat _inrWhole = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 0,
);
final NumberFormat _inrDecimal = NumberFormat.currency(
  locale: 'en_IN',
  symbol: '₹',
  decimalDigits: 2,
);
final NumberFormat _number = NumberFormat.decimalPattern('en_IN');
final DateFormat _dateTime = DateFormat('d MMM, h:mm a', 'en_IN');

String formatInr(num value, {bool decimals = false}) =>
    (decimals ? _inrDecimal : _inrWhole).format(value);

String formatQuantity(num value) => _number.format(value);

String formatDateTime(DateTime value) => _dateTime.format(value.toLocal());

String greetingFor(DateTime time) => switch (time.hour) {
  < 12 => 'Good morning',
  < 17 => 'Good afternoon',
  _ => 'Good evening',
};

String sentenceCase(String value) {
  final words = value.toLowerCase().split('_');
  if (words.isEmpty) return value;
  final phrase = words.join(' ');
  return '${phrase[0].toUpperCase()}${phrase.substring(1)}';
}
