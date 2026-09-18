enum AuthStatus { unauthenticated, authenticated }

class AuthSession {
  const AuthSession._(this.status);

  const AuthSession.unauthenticated() : this._(AuthStatus.unauthenticated);
  const AuthSession.authenticated() : this._(AuthStatus.authenticated);

  final AuthStatus status;

  bool get isAuthenticated => status == AuthStatus.authenticated;
}
