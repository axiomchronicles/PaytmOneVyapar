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
