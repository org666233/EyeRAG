import 'package:shared_preferences/shared_preferences.dart';
import '../constants/app_constants.dart';

class LocalStorage {
  LocalStorage._();
  static final LocalStorage instance = LocalStorage._();

  late SharedPreferences _prefs;

  Future<void> init() async {
    _prefs = await SharedPreferences.getInstance();
  }

  // Token
  String? get token => _prefs.getString(AppConstants.tokenKey);
  Future<void> setToken(String token) =>
      _prefs.setString(AppConstants.tokenKey, token);
  Future<void> clearToken() => _prefs.remove(AppConstants.tokenKey);

  // User ID
  String? get userId => _prefs.getString(AppConstants.userIdKey);
  Future<void> setUserId(String id) =>
      _prefs.setString(AppConstants.userIdKey, id);

  // Theme
  String get themeMode =>
      _prefs.getString(AppConstants.themeModeKey) ?? 'system';
  Future<void> setThemeMode(String mode) =>
      _prefs.setString(AppConstants.themeModeKey, mode);

  // Biometric
  bool get biometricEnabled =>
      _prefs.getBool(AppConstants.biometricEnabledKey) ?? false;
  Future<void> setBiometricEnabled(bool enabled) =>
      _prefs.setBool(AppConstants.biometricEnabledKey, enabled);

  // Saved Username
  String? get savedUsername => _prefs.getString(AppConstants.savedUsernameKey);
  Future<void> setSavedUsername(String username) =>
      _prefs.setString(AppConstants.savedUsernameKey, username);

  Future<void> clearAll() => _prefs.clear();
}
