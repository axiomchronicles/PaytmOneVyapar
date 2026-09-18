import 'package:dio/dio.dart';
import 'package:vyapar/core/auth/token_store.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/auth/models/auth_models.dart';

class AuthRepository {
  AuthRepository(this._dio, this._tokens);

  final Dio _dio;
  final TokenStore _tokens;

  Future<void> signIn({required String email, required String password}) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/token',
        data: {'username': email.trim().toLowerCase(), 'password': password},
        options: Options(contentType: Headers.formUrlEncodedContentType),
      );
      final body = jsonMap(response.data);
      await _saveTokens(body);
      await validateSession();
    } catch (error) {
      try {
        await _tokens.clear();
      } on Object {
        // Preserve the original authentication/network failure.
      }
      throw mapApiError(error);
    }
  }

  Future<void> validateSession() async {
    try {
      await _dio.get<Object?>('/merchants/me');
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<OtpChallenge> requestOtp(
    String phone, {
    required bool registration,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/otp/request',
        data: {
          'identifier': phone,
          'purpose': registration ? 'REGISTRATION' : 'LOGIN',
        },
      );
      return OtpChallenge.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<AuthExchangeResult> verifyOtp({
    required String challengeId,
    required String otp,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/otp/verify',
        data: {'challenge_id': challengeId, 'otp': otp},
      );
      final body = jsonMap(response.data);
      if (body['registration_required'] != true) await _saveTokens(body);
      return AuthExchangeResult.fromJson(body);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<OtpChallenge> resendOtp(String challengeId) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/otp/resend',
        data: {'challenge_id': challengeId},
      );
      return OtpChallenge.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<void> register({
    required String email,
    required String businessName,
    required String storeName,
    required String registrationToken,
    String? password,
    String? phone,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/register',
        data: {
          'email': email.trim().toLowerCase(),
          'business_name': businessName.trim(),
          'store_name': storeName.trim(),
          'registration_token': registrationToken,
          if (password != null) 'password': password,
          if (phone != null) 'phone_number': phone,
        },
      );
      await _saveTokens(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<OAuthChallenge> startOAuth(String provider) async {
    try {
      final response = await _dio.post<Object?>('/auth/oauth/$provider/start');
      return OAuthChallenge.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<AuthExchangeResult> exchangeOAuth({
    required OAuthChallenge challenge,
    required String idToken,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/auth/oauth/${challenge.provider.toLowerCase()}/exchange',
        data: {
          'challenge_id': challenge.id,
          'state': challenge.state,
          'nonce': challenge.nonce,
          'id_token': idToken,
        },
      );
      final body = jsonMap(response.data);
      if (body['registration_required'] != true) await _saveTokens(body);
      return AuthExchangeResult.fromJson(body);
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<void> _saveTokens(JsonMap body) => _tokens.save(
    accessToken: jsonString(body['access_token'], 'access_token'),
    refreshToken: jsonString(body['refresh_token'], 'refresh_token'),
  );

  Future<void> signOut() async {
    final refreshToken = _tokens.refreshToken;
    try {
      await _dio.post<void>(
        '/auth/logout',
        data: {'refresh_token': refreshToken},
      );
    } on Object {
      // Local credential removal remains authoritative for this device.
    } finally {
      await _tokens.clear();
    }
  }
}
