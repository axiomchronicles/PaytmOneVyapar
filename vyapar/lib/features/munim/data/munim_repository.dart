import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';

class MunimChatMessage {
  const MunimChatMessage({
    required this.role,
    required this.content,
    this.timestamp,
  });

  final String role;
  final String content;
  final DateTime? timestamp;
}

class MunimRepository {
  MunimRepository(this._dio);

  final Dio _dio;

  Future<String> sendMessage({
    required String message,
    List<MunimChatMessage> history = const [],
  }) async {
    try {
      final response = await _dio.post<Object?>(
        '/agents/chat',
        data: {
          'message': message,
          'conversation_history': history
              .map((m) => {'role': m.role, 'content': m.content})
              .toList(),
        },
      );
      final body = jsonMap(response.data);
      return jsonString(body['reply'], 'reply');
    } catch (error) {
      throw mapApiError(error);
    }
  }

  Future<Map<String, dynamic>> detectLowStock() async {
    try {
      final response = await _dio.post<Object?>('/agents/detect-low-stock');
      return jsonMap(response.data);
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
