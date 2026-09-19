enum AuthStatus { unauthenticated, authenticated }

class AuthSession {
  const AuthSession._(
    this.status, {
    this.role = 'merchant',
    this.accountType = 'merchant',
    this.businessName = '',
    this.gstin,
    this.pan,
    this.email,
    this.phone,
  });

  const AuthSession.unauthenticated() : this._(AuthStatus.unauthenticated);

  const AuthSession.authenticated({
    String role = 'merchant',
    String accountType = 'merchant',
    String businessName = '',
    String? gstin,
    String? pan,
    String? email,
    String? phone,
  }) : this._(
         AuthStatus.authenticated,
         role: role,
         accountType: accountType,
         businessName: businessName,
         gstin: gstin,
         pan: pan,
         email: email,
         phone: phone,
       );

  final AuthStatus status;
  final String role;
  final String accountType;
  final String businessName;
  final String? gstin;
  final String? pan;
  final String? email;
  final String? phone;

  bool get isAuthenticated => status == AuthStatus.authenticated;
  bool get isSupplier => role.toLowerCase() == 'supplier';
  bool get isMerchant => !isSupplier;
}
