import {
  CognitoIdentityProviderClient,
  SignUpCommand,
  ConfirmSignUpCommand,
  InitiateAuthCommand,
  ForgotPasswordCommand,
  ConfirmForgotPasswordCommand,
} from "@aws-sdk/client-cognito-identity-provider";
import { SettingsManager } from "./SettingsManager";

// Initialize Cognito Client
// Note: In browser, region must be provided, we'll get it from settings.
export class CognitoAuthService {
  private static getClient(): CognitoIdentityProviderClient {
    let settings = SettingsManager.getSettings();
    if (!settings) {
      settings = SettingsManager.loadFromEnvironment();
    }
    if (!settings || !settings.cognito.region) {
      throw new Error("AWS Region is not configured in settings.");
    }
    return new CognitoIdentityProviderClient({ region: settings.cognito.region });
  }

  private static getClientId(): string {
    let settings = SettingsManager.getSettings();
    if (!settings) {
      settings = SettingsManager.loadFromEnvironment();
    }
    if (!settings || !settings.cognito.userPoolClientId) {
      throw new Error("User Pool Client ID is not configured.");
    }
    return settings.cognito.userPoolClientId;
  }

  /**
   * Login with email and password
   */
  static async login(data: any) {
    const client = this.getClient();
    const command = new InitiateAuthCommand({
      AuthFlow: "USER_PASSWORD_AUTH",
      ClientId: this.getClientId(),
      AuthParameters: {
        USERNAME: data.username,
        PASSWORD: data.password,
      },
    });

    try {
      const response = await client.send(command);
      
      // Store the ID token needed for generating AWS Credentials later
      if (response.AuthenticationResult?.IdToken) {
        localStorage.setItem("cognito_id_token", response.AuthenticationResult.IdToken);
      }
      
      return response.AuthenticationResult;
    } catch (error: any) {
      console.error("Cognito Login Error:", error);
      throw new Error(error.message || "Login failed");
    }
  }

  /**
   * Sign up a new user
   */
  static async signup(data: any) {
    const client = this.getClient();
    
    // Convert user attributes into Cognito array format
    const userAttributes = [];
    if (data.email) userAttributes.push({ Name: "email", Value: data.email });
    if (data.firstName) userAttributes.push({ Name: "given_name", Value: data.firstName });
    if (data.lastName) userAttributes.push({ Name: "family_name", Value: data.lastName });
    if (data.gender) userAttributes.push({ Name: "gender", Value: data.gender });

    const command = new SignUpCommand({
      ClientId: this.getClientId(),
      Username: data.username,
      Password: data.password,
      UserAttributes: userAttributes,
    });

    try {
      const response = await client.send(command);
      return response;
    } catch (error: any) {
      console.error("Cognito Signup Error:", error);
      throw new Error(error.message || "Signup failed");
    }
  }

  /**
   * Confirm sign up using verification code
   */
  static async confirmSignup(data: any) {
    const client = this.getClient();
    const command = new ConfirmSignUpCommand({
      ClientId: this.getClientId(),
      Username: data.username,
      ConfirmationCode: data.code,
    });

    try {
      const response = await client.send(command);
      return response;
    } catch (error: any) {
      console.error("Cognito Confirm Signup Error:", error);
      throw new Error(error.message || "Confirmation failed");
    }
  }

  /**
   * Forgot password request
   */
  static async forgotPassword(username: string) {
    const client = this.getClient();
    const command = new ForgotPasswordCommand({
      ClientId: this.getClientId(),
      Username: username,
    });

    try {
      const response = await client.send(command);
      return response;
    } catch (error: any) {
      console.error("Cognito Forgot Password Error:", error);
      throw new Error(error.message || "Failed to send reset code");
    }
  }

  /**
   * Confirm forgot password
   */
  static async confirmForgotPassword(data: any) {
    const client = this.getClient();
    const command = new ConfirmForgotPasswordCommand({
      ClientId: this.getClientId(),
      Username: data.username,
      ConfirmationCode: data.code,
      Password: data.newPassword,
    });

    try {
      const response = await client.send(command);
      return response;
    } catch (error: any) {
      console.error("Cognito Reset Password Error:", error);
      throw new Error(error.message || "Password reset failed");
    }
  }

  /**
   * Logout user locally
   */
  static logout() {
    localStorage.removeItem("cognito_id_token");
  }

  /**
   * Get the saved IdToken
   */
  static getIdToken(): string | null {
    return localStorage.getItem("cognito_id_token");
  }
}
