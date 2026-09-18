import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/procurement/models/agent_run.dart';

class ProcurementRepository {
  ProcurementRepository(this._dio);

  final Dio _dio;

  Future<AgentRunResult> start(AgentRunRequest request) async {
    try {
      final response = await _dio.post<Object?>(
        '/agents/runs',
        data: request.toJson(),
      );
      return AgentRunResult.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
