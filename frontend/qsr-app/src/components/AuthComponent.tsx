"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Mic,
  Mail,
  Lock,
  ArrowRight,
  Loader2,
  CheckCircle2,
  AlertCircle,
  Check,
  X,
} from "lucide-react";
import { CognitoAuthService } from "../services/CognitoAuthService";

export default function AuthComponent({ onSignIn }: { onSignIn: () => void }) {
  const [mode, setMode] = useState<
    "signin" | "signup" | "verify" | "forgot" | "reset"
  >("signin");

  const [formData, setFormData] = useState({
    email: "",
    password: "",
    firstName: "",
    lastName: "",
    gender: "",
    verificationCode: "",
  });

  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    symbol: false,
  });

  const validatePassword = (password: string) => {
    const validations = {
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      symbol: /[^A-Za-z0-9]/.test(password),
    };
    setPasswordValidation(validations);
  };

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [isResendingCode, setIsResendingCode] = useState(false);

  // Name validation states
  const [nameErrors, setNameErrors] = useState({
    firstName: "",
    lastName: "",
  });

  function capitalize(word: string): string {
    if (!word) return "";
    return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
  }

  const validateName = (name: string, field: "firstName" | "lastName") => {
    if (name.length > 0 && name.length < 2) {
      setNameErrors((prev) => ({
        ...prev,
        [field]: "Must be at least 2 characters",
      }));
      return false;
    } else {
      setNameErrors((prev) => ({
        ...prev,
        [field]: "",
      }));
      return true;
    }
  };

  const isPasswordValid = Object.values(passwordValidation).every((valid) => valid);
  const isNamesValid = formData.firstName.length >= 2 && formData.lastName.length >= 2;

  // Handle submit logic
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (mode === "signup") {
      if (!isPasswordValid) {
        setError("Please meet all password requirements");
        return;
      }
      if (!isNamesValid) {
        setError("First and last names must be at least 2 characters");
        return;
      }
    }

    if (mode === "reset") {
      if (!isPasswordValid) {
        setError("Please meet all password requirements");
        return;
      }
    }

    setIsLoading(true);

    try {
      if (mode === "signin") {
        await CognitoAuthService.login({
          username: formData.email,
          password: formData.password,
        });

        setSuccess("Successfully signed in!");
        setTimeout(() => onSignIn(), 1000);
      } else if (mode === "signup") {
        try {
          await CognitoAuthService.signup({
            username: formData.email,
            password: formData.password,
            email: formData.email,
            firstName: capitalize(formData.firstName),
            lastName: capitalize(formData.lastName),
            gender: formData.gender,
          });
          setSuccess("Account created! Please check your email for verification code.");
          setMode("verify");
        } catch (signupError: any) {
          setError(signupError.message || "Signup failed");
        }
      } else if (mode === "verify") {
        await CognitoAuthService.confirmSignup({
          username: formData.email,
          code: formData.verificationCode,
        });
        setSuccess("Email verified! You can now sign in.");
        setTimeout(() => {
          setMode("signin");
          setFormData({ ...formData, verificationCode: "" });
        }, 2000);
      } else if (mode === "forgot") {
        await CognitoAuthService.forgotPassword(formData.email);
        setSuccess("Reset code sent to your email!");
        setMode("reset");
      } else if (mode === "reset") {
        await CognitoAuthService.confirmForgotPassword({
          username: formData.email,
          code: formData.verificationCode,
          newPassword: formData.password,
        });
        setSuccess("Password reset successful! You can now sign in.");
        setTimeout(() => {
          setMode("signin");
          setFormData({
            ...formData,
            verificationCode: "",
            password: "",
          });
        }, 2000);
      }
    } catch (err: any) {
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const features = [
    { icon: "🎙️", text: "Real-time omnichannel voice ordering" },
    { icon: "⚡", text: "Sub-second response with AWS Bedrock" },
    { icon: "🔐", text: "Secure serverless architecture" },
    { icon: "🍔", text: "Interactive smart menu system" },
  ];

  return (
    <div className="min-h-screen bg-gray-950 flex items-center justify-center p-4 relative overflow-hidden">
      {/* Animated Background */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        <motion.div
          animate={{ rotate: [0, 360], scale: [1, 1.2, 1] }}
          transition={{ duration: 20, repeat: Infinity }}
          className="absolute -top-40 -right-40 w-96 h-96 bg-red-600/10 rounded-full blur-3xl"
        />
        <motion.div
          animate={{ rotate: [360, 0], scale: [1, 1.3, 1] }}
          transition={{ duration: 25, repeat: Infinity }}
          className="absolute -bottom-40 -left-40 w-96 h-96 bg-orange-600/10 rounded-full blur-3xl"
        />
      </div>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6 }}
        className="relative w-full max-w-6xl grid lg:grid-cols-2 gap-8 items-center z-10"
      >
        {/* Left Side - Branding */}
        <motion.div
          initial={{ opacity: 0, x: -50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.2, duration: 0.6 }}
          className="space-y-8 p-8"
        >
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="p-3 bg-gradient-to-br from-red-600 to-orange-600 rounded-2xl shadow-lg">
              <Mic size={40} className="text-white" />
            </div>
            <h1 className="text-4xl font-bold text-white">
              QSR Assistant
            </h1>
          </div>

          <h2 className="text-5xl font-bold text-white leading-tight">
            Omnichannel
            <span className="block text-transparent bg-clip-text bg-gradient-to-r from-red-500 to-orange-500">
              Voice Ordering
            </span>
          </h2>

          <p className="text-xl text-gray-400">
            Powered by Amazon Bedrock AgentCore • Next.js • Serverless WebSockets
          </p>

          <div className="space-y-4">
            {features.map((feature, i) => (
              <motion.div
                key={i}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.6 + i * 0.1 }}
                className="flex items-center space-x-3 p-4 bg-gray-900/50 backdrop-blur-md rounded-xl border border-gray-800"
              >
                <span className="text-2xl">{feature.icon}</span>
                <span className="text-gray-300">
                  {feature.text}
                </span>
              </motion.div>
            ))}
          </div>
        </motion.div>

        {/* Right Side - Auth Form */}
        <motion.div
          initial={{ opacity: 0, x: 50 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.3, duration: 0.6 }}
          className="relative"
        >
          <div className="bg-gray-900/80 backdrop-blur-xl rounded-3xl shadow-2xl p-8 border border-gray-800">
            {mode !== "verify" && mode !== "forgot" && mode !== "reset" && (
              <div className="flex space-x-2 mb-6 p-1 bg-gray-950 rounded-xl">
                <button
                  onClick={() => {
                    setMode("signin");
                    setError("");
                    setSuccess("");
                  }}
                  className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
                    mode === "signin"
                      ? "bg-gray-800 text-white shadow-md"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  Sign In
                </button>
                <button
                  onClick={() => {
                    setMode("signup");
                    setError("");
                    setSuccess("");
                  }}
                  className={`flex-1 py-3 px-4 rounded-lg font-medium transition-all ${
                    mode === "signup"
                      ? "bg-gray-800 text-white shadow-md"
                      : "text-gray-500 hover:text-gray-300"
                  }`}
                >
                  Sign Up
                </button>
              </div>
            )}

            <div className="mb-6">
              <h3 className="text-2xl font-bold text-white">
                {mode === "signin" && "Welcome back"}
                {mode === "signup" && "Create your account"}
                {mode === "verify" && "Verify your email"}
                {mode === "forgot" && "Forgot Password"}
                {mode === "reset" && "Reset Password"}
              </h3>
              <p className="text-gray-400 mt-1">
                {mode === "signin" && "Sign in to start ordering"}
                {mode === "signup" && "Join us to try the AI voice assistant"}
                {mode === "verify" && "Enter the code sent to your email"}
                {mode === "forgot" && "Enter your email to reset your password"}
                {mode === "reset" && "Enter the reset code and new password"}
              </p>
            </div>

            <AnimatePresence>
              {error && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-4 p-4 bg-red-900/20 border border-red-800 rounded-xl flex items-center space-x-2"
                >
                  <AlertCircle className="text-red-500" size={20} />
                  <span className="text-red-400 text-sm">{error}</span>
                </motion.div>
              )}
              {success && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  className="mb-4 p-4 bg-green-900/20 border border-green-800 rounded-xl flex items-center space-x-2"
                >
                  <CheckCircle2 className="text-green-500" size={20} />
                  <span className="text-green-400 text-sm">{success}</span>
                </motion.div>
              )}
            </AnimatePresence>

            <form onSubmit={handleSubmit} className="space-y-4">
              <AnimatePresence mode="wait">
                {(mode === "signin" || mode === "signup" || mode === "forgot" || mode === "reset") && (
                  <motion.div key="email">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Email Address</label>
                    <div className="relative">
                      <Mail className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                      <input
                        type="email"
                        required
                        value={formData.email}
                        onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                        className="w-full pl-12 pr-4 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white"
                        placeholder="your@email.com"
                      />
                    </div>
                  </motion.div>
                )}

                {(mode === "signin" || mode === "signup") && (
                  <motion.div key="password">
                    <label className="block text-sm font-medium text-gray-300 mb-2 mt-4">Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={formData.password}
                        onFocus={() => mode === "signup" && setIsPasswordFocused(true)}
                        onBlur={() => setIsPasswordFocused(false)}
                        onChange={(e) => {
                          setFormData({ ...formData, password: e.target.value });
                          if (mode === "signup") validatePassword(e.target.value);
                        }}
                        className="w-full pl-12 pr-12 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white"
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-300"
                      >
                        {showPassword ? "👁️" : "👁️‍🗨️"}
                      </button>
                    </div>

                    {mode === "signup" && isPasswordFocused && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 p-3 bg-gray-950 rounded-lg border border-gray-800"
                      >
                        <p className="text-xs font-medium text-gray-400 mb-2">Password must contain:</p>
                        <div className="space-y-1">
                          <PasswordRequirement met={passwordValidation.length} text="At least 8 characters" />
                          <PasswordRequirement met={passwordValidation.uppercase} text="One uppercase letter" />
                          <PasswordRequirement met={passwordValidation.lowercase} text="One lowercase letter" />
                          <PasswordRequirement met={passwordValidation.number} text="One number" />
                          <PasswordRequirement met={passwordValidation.symbol} text="One special character" />
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                )}

                {mode === "signup" && (
                  <>
                    <motion.div key="firstName" className="mt-4">
                      <label className="block text-sm font-medium text-gray-300 mb-2">First Name</label>
                      <input
                        type="text"
                        required
                        value={formData.firstName}
                        onChange={(e) => {
                          setFormData({ ...formData, firstName: e.target.value });
                          validateName(e.target.value, "firstName");
                        }}
                        className={`w-full px-4 py-3 border ${nameErrors.firstName ? "border-red-500" : "border-gray-700"} rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white`}
                        placeholder="John"
                      />
                    </motion.div>

                    <motion.div key="lastName" className="mt-4">
                      <label className="block text-sm font-medium text-gray-300 mb-2">Last Name</label>
                      <input
                        type="text"
                        required
                        value={formData.lastName}
                        onChange={(e) => {
                          setFormData({ ...formData, lastName: e.target.value });
                          validateName(e.target.value, "lastName");
                        }}
                        className={`w-full px-4 py-3 border ${nameErrors.lastName ? "border-red-500" : "border-gray-700"} rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white`}
                        placeholder="Doe"
                      />
                    </motion.div>

                    <motion.div key="gender" className="mt-4">
                      <label className="block text-sm font-medium text-gray-300 mb-2">Gender</label>
                      <select
                        required
                        value={formData.gender}
                        onChange={(e) => setFormData({ ...formData, gender: e.target.value })}
                        className="w-full px-4 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white"
                      >
                        <option value="" disabled>Select gender</option>
                        <option value="male">Male</option>
                        <option value="female">Female</option>
                        <option value="other">Other</option>
                      </select>
                    </motion.div>
                  </>
                )}

                {mode === "verify" && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <label className="block text-sm font-medium text-gray-300 mb-2">Verification Code</label>
                    <input
                      type="text"
                      required
                      value={formData.verificationCode}
                      onChange={(e) => setFormData({ ...formData, verificationCode: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white text-center text-2xl tracking-widest"
                      placeholder="123456"
                      maxLength={6}
                    />
                  </motion.div>
                )}

                {mode === "reset" && (
                  <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} key="reset-code">
                    <label className="block text-sm font-medium text-gray-300 mb-2">Reset Code</label>
                    <input
                      type="text"
                      required
                      value={formData.verificationCode}
                      onChange={(e) => setFormData({ ...formData, verificationCode: e.target.value })}
                      className="w-full px-4 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white text-center text-2xl tracking-widest"
                      placeholder="123456"
                      maxLength={6}
                    />
                    <label className="block text-sm font-medium text-gray-300 mb-2 mt-4">New Password</label>
                    <div className="relative">
                      <Lock className="absolute left-4 top-1/2 transform -translate-y-1/2 text-gray-500" size={20} />
                      <input
                        type={showPassword ? "text" : "password"}
                        required
                        value={formData.password}
                        onFocus={() => setIsPasswordFocused(true)}
                        onBlur={() => setIsPasswordFocused(false)}
                        onChange={(e) => {
                          setFormData({ ...formData, password: e.target.value });
                          validatePassword(e.target.value);
                        }}
                        className="w-full pl-12 pr-12 py-3 border border-gray-700 rounded-xl focus:ring-2 focus:ring-red-500 bg-gray-950 text-white"
                        placeholder="••••••••"
                      />
                      <button
                        type="button"
                        onClick={() => setShowPassword(!showPassword)}
                        className="absolute right-4 top-1/2 transform -translate-y-1/2 text-gray-500 hover:text-gray-300"
                      >
                        {showPassword ? "👁️" : "👁️‍🗨️"}
                      </button>
                    </div>

                    {isPasswordFocused && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        exit={{ opacity: 0, height: 0 }}
                        className="mt-3 p-3 bg-gray-950 rounded-lg border border-gray-800"
                      >
                        <p className="text-xs font-medium text-gray-400 mb-2">Password must contain:</p>
                        <div className="space-y-1">
                          <PasswordRequirement met={passwordValidation.length} text="At least 8 characters" />
                          <PasswordRequirement met={passwordValidation.uppercase} text="One uppercase letter" />
                          <PasswordRequirement met={passwordValidation.lowercase} text="One lowercase letter" />
                          <PasswordRequirement met={passwordValidation.number} text="One number" />
                          <PasswordRequirement met={passwordValidation.symbol} text="One special character" />
                        </div>
                      </motion.div>
                    )}
                  </motion.div>
                )}
              </AnimatePresence>

              {mode === "signin" && (
                <div className="flex items-center justify-between text-sm mt-4">
                  <label className="flex items-center text-gray-400">
                    <input type="checkbox" className="mr-2 rounded border-gray-700 bg-gray-950" />
                    Remember me
                  </label>
                  <button
                    type="button"
                    onClick={() => setMode("forgot")}
                    className="text-red-500 hover:text-red-400 font-medium"
                  >
                    Forgot password?
                  </button>
                </div>
              )}

              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 px-4 bg-gradient-to-r from-red-600 to-orange-600 hover:from-red-700 hover:to-orange-700 text-white rounded-xl font-medium shadow-lg hover:shadow-red-500/25 transition-all flex items-center justify-center space-x-2 disabled:opacity-70 disabled:cursor-not-allowed mt-6"
              >
                {isLoading ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <>
                    <span>
                      {mode === "signin" && "Sign In"}
                      {mode === "signup" && "Create Account"}
                      {mode === "verify" && "Verify Email"}
                      {mode === "forgot" && "Send Reset Link"}
                      {mode === "reset" && "Reset Password"}
                    </span>
                    <ArrowRight size={20} />
                  </>
                )}
              </button>
            </form>
          </div>
        </motion.div>
      </motion.div>
    </div>
  );
}

function PasswordRequirement({ met, text }: { met: boolean; text: string }) {
  return (
    <div className="flex items-center space-x-2">
      {met ? (
        <Check size={14} className="text-green-500" />
      ) : (
        <X size={14} className="text-gray-600" />
      )}
      <span className={`text-xs ${met ? "text-gray-300" : "text-gray-600"}`}>
        {text}
      </span>
    </div>
  );
}
