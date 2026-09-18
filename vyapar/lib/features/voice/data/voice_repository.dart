import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/voice/models/voice_models.dart';

class VoiceRepository {
  VoiceRepository(this._dio);

  final Dio _dio;

  Future<VoiceSessionInfo> createSession({
    required String languageCode,
    String? proposalId,
    String? requestId,
    String? approvalToken,
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/voice/sessions',
        data: {
          'language_code': languageCode,
          'sample_rate': 16000,
          'encoding': 'linear16',
          if (proposalId != null) 'active_proposal_id': proposalId,
          if (requestId != null) 'active_request_id': requestId,
          if (approvalToken != null) 'approval_token': approvalToken,
        },
      );
      return VoiceSessionInfo.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
