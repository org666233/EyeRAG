import 'package:flutter/foundation.dart';
import 'package:sqflite/sqflite.dart';
import 'package:path/path.dart';
import '../constants/app_constants.dart';

/// 本地数据库（收藏缓存）
/// - 移动端（iOS/Android）：sqflite
/// - Web：内存列表（刷新后清空，Web 端靠网络实时获取）
class LocalDb {
  LocalDb._();
  static final LocalDb instance = LocalDb._();

  Database? _db;

  // Web 平台使用内存存储
  final List<Map<String, dynamic>> _memFavorites = [];

  Future<Database?> get _database async {
    if (kIsWeb) return null;
    _db ??= await _open();
    return _db;
  }

  Future<Database> _open() async {
    final dir = await getDatabasesPath();
    return openDatabase(
      join(dir, AppConstants.dbName),
      version: AppConstants.dbVersion,
      onCreate: (db, version) async {
        await db.execute('''
          CREATE TABLE favorites (
            id TEXT PRIMARY KEY,
            message_id TEXT,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,
            created_at TEXT NOT NULL
          )
        ''');
      },
    );
  }

  // ---- 收藏 CRUD ----

  Future<void> upsertFavorite(Map<String, dynamic> data) async {
    if (kIsWeb) {
      _memFavorites.removeWhere((f) => f['id'] == data['id']);
      _memFavorites.insert(0, Map<String, dynamic>.from(data));
      return;
    }
    final db = await _database;
    await db!.insert(
      'favorites',
      data,
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  Future<List<Map<String, dynamic>>> getFavorites() async {
    if (kIsWeb) return List<Map<String, dynamic>>.from(_memFavorites);
    final db = await _database;
    return db!.query('favorites', orderBy: 'created_at DESC');
  }

  Future<void> deleteFavorite(String id) async {
    if (kIsWeb) {
      _memFavorites.removeWhere((f) => f['id'] == id);
      return;
    }
    final db = await _database;
    await db!.delete('favorites', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> clearFavorites() async {
    if (kIsWeb) {
      _memFavorites.clear();
      return;
    }
    final db = await _database;
    await db!.delete('favorites');
  }
}
