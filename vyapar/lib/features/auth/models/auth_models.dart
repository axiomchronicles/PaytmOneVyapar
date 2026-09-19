import 'package:vyapar/core/networking/json.dart';

class OtpChallenge {
  const OtpChallenge({
    required this.id,
    required this.destination,
    required this.expiresAt,
    required this.resendAvailableAt,
  });

  factory OtpChallenge.fromJson(JsonMap json) => OtpChallenge(
    id: jsonString(json['challenge_id'], 'challenge_id'),
    destination: jsonString(json['destination'], 'destination'),
    expiresAt: DateTime.parse(jsonString(json['expires_at'], 'expires_at')),
    resendAvailableAt: DateTime.parse(
      jsonString(json['resend_available_at'], 'resend_available_at'),
    ),
  );

  final String id;
  final String destination;
  final DateTime expiresAt;
  final DateTime resendAvailableAt;
}

class AuthExchangeResult {
  const AuthExchangeResult({
    required this.registrationRequired,
    this.registrationToken,
    this.email,
  });

  factory AuthExchangeResult.fromJson(JsonMap json) => AuthExchangeResult(
    registrationRequired: json['registration_required'] == true,
    registrationToken: jsonOptionalString(json['registration_token']),
    email: jsonOptionalString(json['email']),
  );

  final bool registrationRequired;
  final String? registrationToken;
  final String? email;
}

class OAuthChallenge {
  const OAuthChallenge({
    required this.id,
    required this.provider,
    required this.state,
    required this.nonce,
    required this.clientId,
  });

  factory OAuthChallenge.fromJson(JsonMap json) => OAuthChallenge(
    id: jsonString(json['challenge_id'], 'challenge_id'),
    provider: jsonString(json['provider'], 'provider'),
    state: jsonString(json['state'], 'state'),
    nonce: jsonString(json['nonce'], 'nonce'),
    clientId: jsonString(json['client_id'], 'client_id'),
  );

  final String id;
  final String provider;
  final String state;
  final String nonce;
  final String clientId;
}

class UserMe {
  const UserMe({
    required this.userId,
    required this.merchantId,
    required this.role,
    required this.accountType,
    required this.email,
    required this.businessName,
    this.phoneNumber,
    this.gstin,
    this.pan,
  });

  factory UserMe.fromJson(JsonMap json) => UserMe(
    userId: jsonString(json['user_id'], 'user_id'),
    merchantId: jsonString(json['merchant_id'], 'merchant_id'),
    role: jsonOptionalString(json['role']) ?? 'merchant',
    accountType: jsonOptionalString(json['account_type']) ?? 'merchant',
    email: jsonString(json['email'], 'email'),
    businessName: jsonOptionalString(json['business_name']) ?? 'My Business',
    phoneNumber: jsonOptionalString(json['phone_number']),
    gstin: jsonOptionalString(json['gstin']),
    pan: jsonOptionalString(json['pan']),
  );

  final String userId;
  final String merchantId;
  final String role;
  final String accountType;
  final String email;
  final String businessName;
  final String? phoneNumber;
  final String? gstin;
  final String? pan;
}
