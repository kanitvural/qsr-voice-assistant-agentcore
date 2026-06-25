"use client";

import { useState, useEffect } from 'react';
import { fromCognitoIdentityPool } from '@aws-sdk/credential-providers';
import { SettingsManager } from '@/services/SettingsManager';
import AuthComponent from '@/components/AuthComponent';
import { ChatInterface } from '@/components/ChatInterface';
import { CognitoAuthService } from '@/services/CognitoAuthService';
import type { AppSettings, AWSCredentials } from '@/services/SettingsManager';

type AppState = 'auth' | 'chat' | 'error' | 'loading';

export default function Home() {
  const [appState, setAppState] = useState<AppState>('loading');
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [credentials, setCredentials] = useState<AWSCredentials | null>(null);
  const [accessToken, setAccessToken] = useState<string>('');
  const [error, setError] = useState<string>('');

  const initializeApp = async () => {
    setAppState('loading');
    const envSettings = SettingsManager.loadFromEnvironment();
    
    if (!envSettings) {
      setError('Application not configured. Please check environment variables.');
      setAppState('error');
      return;
    }

    setSettings(envSettings);
    SettingsManager.saveSettings(envSettings);
    
    try {
      const idToken = CognitoAuthService.getIdToken();

      if (idToken) {
        const credentialsProvider = fromCognitoIdentityPool({
          clientConfig: { region: envSettings.cognito.region },
          identityPoolId: envSettings.cognito.identityPoolId,
          logins: {
            [`cognito-idp.${envSettings.cognito.region}.amazonaws.com/${envSettings.cognito.userPoolId}`]: idToken
          }
        });

        const awsCredentials = await credentialsProvider();

        const formattedCredentials: AWSCredentials = {
          AccessKeyId: awsCredentials.accessKeyId,
          SecretKey: awsCredentials.secretAccessKey,
          SessionToken: awsCredentials.sessionToken || '',
          Expiration: awsCredentials.expiration?.toISOString() || new Date(Date.now() + 3600000).toISOString()
        };

        SettingsManager.saveCredentials(formattedCredentials);
        setCredentials(formattedCredentials);
        setAccessToken(idToken); // For our case, IdToken acts as the main auth token
        setAppState('chat');
        return;
      }
    } catch (error) {
      console.log('No valid session found or session expired, showing auth screen');
      CognitoAuthService.logout();
    }

    setAppState('auth');
  };

  useEffect(() => {
    initializeApp();
  }, []);

  const handleAuthSuccess = () => {
    // When AuthComponent finishes login, it saves the ID token.
    // Re-initialize the app to fetch the AWS credentials using the new token.
    initializeApp();
  };

  const handleSignOut = () => {
    try {
      CognitoAuthService.logout();
      SettingsManager.clearCredentials();
      setCredentials(null);
      setAccessToken('');
      setAppState('auth');
    } catch (error) {
      console.error('Error signing out:', error);
    }
  };

  if (appState === 'error') {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
        <div className="bg-gray-900/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-gray-800 max-w-md text-center">
          <h2 className="text-2xl font-bold text-red-500 mb-4">⚠️ Configuration Error</h2>
          <p className="text-gray-400">{error}</p>
        </div>
      </div>
    );
  }

  if (appState === 'auth' && settings) {
    return <AuthComponent onSignIn={handleAuthSuccess} />;
  }

  if (appState === 'chat' && settings && credentials) {
    return (
      <ChatInterface
        settings={settings}
        credentials={credentials}
        accessToken={accessToken}
        onSignOut={handleSignOut}
      />
    );
  }

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4">
      <div className="bg-gray-900/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-gray-800">
        <h2 className="text-xl font-bold text-white flex items-center space-x-3">
          <div className="w-6 h-6 border-2 border-red-500 border-t-transparent rounded-full animate-spin"></div>
          <span>Loading QSR Assistant...</span>
        </h2>
      </div>
    </div>
  );
}
