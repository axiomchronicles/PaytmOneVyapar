import 'package:decimal/decimal.dart';
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

num _numeric(Object value) =>
    value is Decimal ? double.parse(value.toString()) : value as num;

String formatInr(Object value, {bool decimals = false}) =>
    (decimals ? _inrDecimal : _inrWhole).format(_numeric(value));

String formatQuantity(Object value) => _number.format(_numeric(value));

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
