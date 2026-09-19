import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:vyapar/core/errors/app_failure.dart';
import 'package:vyapar/core/networking/api_error_mapper.dart';

void main() {
  test('exposes the first field-level API validation error', () {
    final failure = mapApiError(
      DioException(
        requestOptions: RequestOptions(path: '/auth/otp/verify'),
        response: Response<Object?>(
          requestOptions: RequestOptions(path: '/auth/otp/verify'),
          statusCode: 422,
          data: {
            'error': {
              'code': 'VALIDATION_FAILED',
              'message': 'Request validation failed',
              'details': {
                'errors': [
                  {
                    'loc': ['body', 'otp'],
                    'msg': 'String should match pattern \\A\\d{6}\\z',
                    'type': 'string_pattern_mismatch',
                  },
                ],
              },
            },
          },
        ),
        type: DioExceptionType.badResponse,
      ),
    );

    expect(failure.kind, FailureKind.validation);
    expect(failure.message, 'otp: String should match pattern \\A\\d{6}\\z');
  });
}
