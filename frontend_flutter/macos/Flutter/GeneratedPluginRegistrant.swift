//
//  Generated file. Do not edit.
//

import FlutterMacOS
import Foundation

import local_auth_darwin
import package_info_plus
import share_plus
import shared_preferences_foundation
import speech_to_text
import sqflite_darwin

func RegisterGeneratedPlugins(registry: FlutterPluginRegistry) {
  LocalAuthPlugin.register(with: registry.registrar(forPlugin: "LocalAuthPlugin"))
  FPPPackageInfoPlusPlugin.register(with: registry.registrar(forPlugin: "FPPPackageInfoPlusPlugin"))
  SharePlusMacosPlugin.register(with: registry.registrar(forPlugin: "SharePlusMacosPlugin"))
  SharedPreferencesPlugin.register(with: registry.registrar(forPlugin: "SharedPreferencesPlugin"))
  SpeechToTextPlugin.register(with: registry.registrar(forPlugin: "SpeechToTextPlugin"))
  SqflitePlugin.register(with: registry.registrar(forPlugin: "SqflitePlugin"))
}
