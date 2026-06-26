import {
  CognitoIdentityProviderClient,
  InitiateAuthCommand,
  GetUserCommand,
  SignUpCommand,
  ConfirmSignUpCommand,
  ResendConfirmationCodeCommand,
  ForgotPasswordCommand,
  ConfirmForgotPasswordCommand,
} from "@aws-sdk/client-cognito-identity-provider";
import { fromCognitoIdentityPool } from "@aws-sdk/credential-providers";
import { useConfigStore } from "@/store/useConfigStore";

const getCognitoClient = (region: string) => new CognitoIdentityProviderClient({ region });

export interface AuthSession {
  accessToken: string;
  idToken: string;
  refreshToken?: string;
  expiresIn: number;
}

export interface AWSCredentials {
  accessKeyId: string;
  secretAccessKey: string;
  sessionToken: string;
  expiration?: Date;
}

// ---------------------------------------------
// Authentication Flows
// ---------------------------------------------

export async function login(username: string, password: string): Promise<AuthSession> {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");
  
  const command = new InitiateAuthCommand({
    AuthFlow: "USER_PASSWORD_AUTH",
    ClientId: config.clientId,
    AuthParameters: {
      USERNAME: username,
      PASSWORD: password,
    },
  });

  const response = await getCognitoClient(config.region).send(command);
  if (!response.AuthenticationResult) {
    throw new Error("Authentication failed: No result returned");
  }

  return {
    accessToken: response.AuthenticationResult.AccessToken!,
    idToken: response.AuthenticationResult.IdToken!,
    refreshToken: response.AuthenticationResult.RefreshToken,
    expiresIn: response.AuthenticationResult.ExpiresIn || 3600,
  };
}

export async function signUp(email: string, password: string, firstName: string, lastName: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  // Since User Pool uses email as an alias, Username cannot be an email format.
  // We generate a clean, unique string for the Cognito Username.
  const cleanPrefix = email.split("@")[0].replace(/[^a-zA-Z0-9]/g, "");
  const uniqueSuffix = Math.random().toString(36).substring(2, 8);
  const generatedUsername = `${cleanPrefix}_${uniqueSuffix}`;

  const command = new SignUpCommand({
    ClientId: config.clientId,
    Username: generatedUsername,
    Password: password,
    UserAttributes: [
      { Name: "email", Value: email },
      { Name: "name", Value: `${firstName} ${lastName}` },
      { Name: "given_name", Value: firstName },
      { Name: "family_name", Value: lastName },
    ],
  });
  const response = await getCognitoClient(config.region).send(command);
  return { ...response, generatedUsername };
}

export async function confirmSignUp(username: string, code: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const command = new ConfirmSignUpCommand({
    ClientId: config.clientId,
    Username: username,
    ConfirmationCode: code,
  });
  return getCognitoClient(config.region).send(command);
}

export async function resendConfirmationCode(username: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const command = new ResendConfirmationCodeCommand({
    ClientId: config.clientId,
    Username: username,
  });
  return getCognitoClient(config.region).send(command);
}

export async function forgotPassword(email: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const command = new ForgotPasswordCommand({
    ClientId: config.clientId,
    Username: email,
  });
  return getCognitoClient(config.region).send(command);
}

export async function confirmForgotPassword(email: string, code: string, newPassword: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const command = new ConfirmForgotPasswordCommand({
    ClientId: config.clientId,
    Username: email,
    ConfirmationCode: code,
    Password: newPassword,
  });
  return getCognitoClient(config.region).send(command);
}

export async function getUserProfile(accessToken: string) {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const command = new GetUserCommand({
    AccessToken: accessToken,
  });
  const response = await getCognitoClient(config.region).send(command);
  return response.UserAttributes;
}

export async function getAwsCredentials(idToken: string): Promise<AWSCredentials> {
  const config = useConfigStore.getState().config;
  if (!config) throw new Error("Config not loaded");

  const credentialsProvider = fromCognitoIdentityPool({
    clientConfig: { region: config.region },
    identityPoolId: config.identityPoolId,
    logins: {
      [`cognito-idp.${config.region}.amazonaws.com/${config.userPoolId}`]: idToken,
    },
  });

  const credentials = await credentialsProvider();
  return {
    accessKeyId: credentials.accessKeyId,
    secretAccessKey: credentials.secretAccessKey,
    sessionToken: credentials.sessionToken || "",
    expiration: credentials.expiration,
  };
}

// ---------------------------------------------
// Session Management
// ---------------------------------------------

export function saveSession(session: AuthSession, credentials: AWSCredentials) {
  if (typeof window !== "undefined") {
    localStorage.setItem("qsr_auth_session", JSON.stringify(session));
    localStorage.setItem("qsr_aws_credentials", JSON.stringify(credentials));
  }
}

export function getStoredSession(): { session: AuthSession | null; credentials: AWSCredentials | null } {
  if (typeof window === "undefined") {
    return { session: null, credentials: null };
  }
  const sessionStr = localStorage.getItem("qsr_auth_session");
  const credsStr = localStorage.getItem("qsr_aws_credentials");

  return {
    session: sessionStr ? JSON.parse(sessionStr) : null,
    credentials: credsStr ? JSON.parse(credsStr) : null,
  };
}

export function clearSession() {
  if (typeof window !== "undefined") {
    localStorage.removeItem("qsr_auth_session");
    localStorage.removeItem("qsr_aws_credentials");
  }
}
