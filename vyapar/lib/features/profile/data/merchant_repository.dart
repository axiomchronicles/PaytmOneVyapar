import 'package:dio/dio.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';
import 'package:vyapar/core/networking/json.dart';
import 'package:vyapar/features/profile/models/merchant_profile.dart';

class MerchantRepository {
  MerchantRepository(this._dio);

  final Dio _dio;

  Future<MerchantProfile> getProfile() async {
    try {
      final response = await _dio.get<Object?>('/merchants/me');
      return MerchantProfile.fromJson(jsonMap(response.data));
    } catch (error) {
      throw mapApiError(error);
    }
  }
}
