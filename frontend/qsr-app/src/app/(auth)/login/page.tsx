"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { motion, AnimatePresence } from "framer-motion";
import { ChefHat, Loader2, ArrowRight, ArrowLeft, Mail, Lock, User, KeyRound, CheckCircle2, AlertCircle, Eye, EyeOff } from "lucide-react";
import {
  login,
  signUp,
  confirmSignUp,
  resendConfirmationCode,
  forgotPassword,
  confirmForgotPassword,
  getAwsCredentials,
  saveSession,
} from "@/lib/cognito";

type AuthMode = "signin" | "signup" | "verify" | "forgot" | "reset";

const ValidationItem = ({ label, isValid }: { label: string; isValid: boolean }) => (
  <div className={`flex items-center gap-1.5 ${isValid ? "text-green-400" : "text-gray-500"}`}>
    {isValid ? <CheckCircle2 size={12} /> : <AlertCircle size={12} />}
    <span>{label}</span>
  </div>
);

export default function AuthPage() {
  const router = useRouter();
  const [mode, setMode] = useState<AuthMode>("signin");
  
  const [formData, setFormData] = useState({
    email: "",
    password: "",
    firstName: "",
    lastName: "",
    verificationCode: "",
  });

  const [passwordValidation, setPasswordValidation] = useState({
    length: false,
    uppercase: false,
    lowercase: false,
    number: false,
    symbol: false,
  });

  const [nameErrors, setNameErrors] = useState({
    firstName: "",
    lastName: "",
  });

  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [isPasswordFocused, setIsPasswordFocused] = useState(false);
  const [cognitoUsername, setCognitoUsername] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const validatePassword = (password: string) => {
    setPasswordValidation({
      length: password.length >= 8,
      uppercase: /[A-Z]/.test(password),
      lowercase: /[a-z]/.test(password),
      number: /[0-9]/.test(password),
      symbol: /[^A-Za-z0-9]/.test(password),
    });
  };

  const validateName = (name: string, field: "firstName" | "lastName") => {
    if (name.length > 0 && name.length < 2) {
      setNameErrors((prev) => ({ ...prev, [field]: "Must be at least 2 characters" }));
      return false;
    } else {
      setNameErrors((prev) => ({ ...prev, [field]: "" }));
      return true;
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    // Auto-capitalize first letter for names
    let finalValue = value;
    if (name === "firstName" || name === "lastName") {
      finalValue = value.charAt(0).toUpperCase() + value.slice(1).toLowerCase();
      validateName(finalValue, name);
    }
    
    setFormData((prev) => ({ ...prev, [name]: finalValue }));
    
    if (name === "password") {
      validatePassword(value);
    }
  };

  const isPasswordValid = Object.values(passwordValidation).every((valid) => valid);
  const isNamesValid = formData.firstName.length >= 2 && formData.lastName.length >= 2;

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    setSuccess("");

    if (mode === "signup" && (!isPasswordValid || !isNamesValid)) {
      setError("Please fix all validation errors before submitting.");
      return;
    }
    if (mode === "reset" && !isPasswordValid) {
      setError("Please meet all password requirements.");
      return;
    }

    setIsLoading(true);

    try {
      if (mode === "signin") {
        const session = await login(formData.email, formData.password);
        const credentials = await getAwsCredentials(session.idToken);
        saveSession(session, credentials);
        router.replace("/");
      } 
      else if (mode === "signup") {
        const result = await signUp(formData.email, formData.password, formData.firstName, formData.lastName);
        setCognitoUsername(result.generatedUsername);
        setSuccess("Account created! Check your email for the code.");
        setMode("verify");
      } 
      else if (mode === "verify") {
        await confirmSignUp(cognitoUsername || formData.email, formData.verificationCode);
        setSuccess("Email verified! You can now sign in.");
        setTimeout(() => setMode("signin"), 2000);
      } 
      else if (mode === "forgot") {
        await forgotPassword(formData.email);
        setSuccess("Reset code sent to your email!");
        setMode("reset");
      } 
      else if (mode === "reset") {
        await confirmForgotPassword(formData.email, formData.verificationCode, formData.password);
        setSuccess("Password reset successful! You can now sign in.");
        setTimeout(() => setMode("signin"), 2000);
      }

    } catch (err: any) {
      console.error(err);
      setError(err.message || "An error occurred. Please try again.");
    } finally {
      setIsLoading(false);
    }
  };

  const resendCode = async () => {
    if (!formData.email) return setError("Email is required to resend code.");
    setError("");
    setSuccess("");
    setIsLoading(true);
    try {
      await resendConfirmationCode(cognitoUsername || formData.email);
      setSuccess("Code resent successfully!");
    } catch (err: any) {
      setError(err.message || "Failed to resend code.");
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col items-center justify-center w-full min-h-[600px]">
      <motion.div
        layout
        className="glass-panel-dark w-full rounded-3xl p-8 relative overflow-hidden"
      >
        <div className="mb-8 flex flex-col items-center">
          <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-qsr-red text-white shadow-lg shadow-qsr-red/30">
            <ChefHat size={32} />
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-white">QSR Voice AI</h1>
          <p className="mt-1 text-sm text-gray-400 capitalize">
            {mode === "signin" && "Sign in to your account"}
            {mode === "signup" && "Create a new account"}
            {mode === "verify" && "Verify your email address"}
            {mode === "forgot" && "Reset your password"}
            {mode === "reset" && "Enter new password"}
          </p>
        </div>

        <AnimatePresence mode="wait">
          {error && (
            <motion.div key="error" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }} className="mb-4 rounded-lg bg-red-500/20 px-4 py-3 text-sm text-red-200 border border-red-500/30">
              {error}
            </motion.div>
          )}
          {success && (
            <motion.div key="success" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }} className="mb-4 rounded-lg bg-green-500/20 px-4 py-3 text-sm text-green-200 border border-green-500/30">
              {success}
            </motion.div>
          )}
        </AnimatePresence>

        <form onSubmit={handleAuth} className="flex flex-col gap-4">
          <AnimatePresence mode="wait">
            
            {/* SIGN IN MODE */}
            {mode === "signin" && (
              <motion.div key="signin" initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: 20 }} className="flex flex-col gap-4">
                
                <div className="relative flex items-center">
                  <Mail className="absolute left-4 text-gray-500" size={18} />
                  <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Email address" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none transition-colors focus:border-qsr-red focus:bg-black/80" />
                </div>
                
                <div className="relative flex items-center">
                  <Lock className="absolute left-4 text-gray-500" size={18} />
                  <input type={showPassword ? "text" : "password"} name="password" value={formData.password} onChange={handleChange} placeholder="Password" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-12 text-sm text-white placeholder-gray-500 outline-none transition-colors focus:border-qsr-red focus:bg-black/80" />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 text-gray-400 hover:text-white transition-colors focus:outline-none">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>

                <div className="flex justify-end">
                  <button type="button" onClick={() => setMode("forgot")} className="text-xs text-qsr-red hover:underline">Forgot password?</button>
                </div>
                
                <button type="submit" disabled={isLoading} className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-qsr-red px-4 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70">
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : "Sign In"}
                  {!isLoading && <ArrowRight size={16} />}
                </button>
                <p className="mt-4 text-center text-xs text-gray-400">
                  Don't have an account? <button type="button" onClick={() => setMode("signup")} className="font-semibold text-white hover:underline">Sign up</button>
                </p>
              </motion.div>
            )}

            {/* SIGN UP MODE */}
            {mode === "signup" && (
              <motion.div key="signup" initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0, x: -20 }} className="flex flex-col gap-4">
                <div className="flex gap-4">
                  <div className="relative flex flex-col w-full">
                    <div className="relative flex items-center">
                      <User className="absolute left-4 text-gray-500" size={18} />
                      <input type="text" name="firstName" value={formData.firstName} onChange={handleChange} placeholder="First Name" required className={`w-full rounded-xl border ${nameErrors.firstName ? "border-red-500" : "border-white/10"} bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80`} />
                    </div>
                    {nameErrors.firstName && <span className="text-xs text-red-500 mt-1 ml-1">{nameErrors.firstName}</span>}
                  </div>
                  <div className="relative flex flex-col w-full">
                    <div className="relative flex items-center">
                      <User className="absolute left-4 text-gray-500" size={18} />
                      <input type="text" name="lastName" value={formData.lastName} onChange={handleChange} placeholder="Last Name" required className={`w-full rounded-xl border ${nameErrors.lastName ? "border-red-500" : "border-white/10"} bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80`} />
                    </div>
                    {nameErrors.lastName && <span className="text-xs text-red-500 mt-1 ml-1">{nameErrors.lastName}</span>}
                  </div>
                </div>
                
                <div className="relative flex items-center">
                  <Mail className="absolute left-4 text-gray-500" size={18} />
                  <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Email address" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>

                <div className="relative flex items-center">
                  <Lock className="absolute left-4 text-gray-500" size={18} />
                  <input type={showPassword ? "text" : "password"} name="password" value={formData.password} onChange={handleChange} onFocus={() => setIsPasswordFocused(true)} onBlur={() => setIsPasswordFocused(false)} placeholder="Create a password" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-12 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 text-gray-400 hover:text-white transition-colors focus:outline-none">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>
                
                <AnimatePresence>
                  {isPasswordFocused && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, marginTop: 0 }}
                      animate={{ opacity: 1, height: "auto", marginTop: 8 }}
                      exit={{ opacity: 0, height: 0, marginTop: 0 }}
                      className="overflow-hidden rounded-xl border border-white/10 bg-black/40 p-4"
                    >
                      <p className="mb-2 text-xs font-semibold text-gray-300">Password Requirements:</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <ValidationItem label="8+ characters" isValid={passwordValidation.length} />
                        <ValidationItem label="Uppercase letter" isValid={passwordValidation.uppercase} />
                        <ValidationItem label="Lowercase letter" isValid={passwordValidation.lowercase} />
                        <ValidationItem label="Number" isValid={passwordValidation.number} />
                        <ValidationItem label="Special character" isValid={passwordValidation.symbol} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
                
                <button type="submit" disabled={isLoading} className="mt-2 flex w-full items-center justify-center gap-2 rounded-xl bg-qsr-red px-4 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70">
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : "Create Account"}
                </button>
                <p className="mt-4 text-center text-xs text-gray-400">
                  Already have an account? <button type="button" onClick={() => setMode("signin")} className="font-semibold text-white hover:underline">Sign in</button>
                </p>
              </motion.div>
            )}

            {/* VERIFY MODE */}
            {mode === "verify" && (
              <motion.div key="verify" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="flex flex-col gap-4">
                <div className="relative flex items-center">
                  <Mail className="absolute left-4 text-gray-500" size={18} />
                  <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Email address" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>
                <div className="relative flex items-center">
                  <KeyRound className="absolute left-4 text-gray-500" size={18} />
                  <input type="text" name="verificationCode" value={formData.verificationCode} onChange={handleChange} placeholder="6-digit verification code" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>
                
                <button type="submit" disabled={isLoading} className="mt-2 flex w-full items-center justify-center rounded-xl bg-qsr-red px-4 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70">
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : "Verify Email"}
                </button>
                <div className="mt-4 flex justify-between text-xs">
                  <button type="button" onClick={() => setMode("signin")} className="flex items-center gap-1 text-gray-400 hover:text-white"><ArrowLeft size={14}/> Back</button>
                  <button type="button" onClick={resendCode} disabled={isLoading} className="text-qsr-red hover:underline">Resend Code</button>
                </div>
              </motion.div>
            )}

            {/* FORGOT PASSWORD MODE */}
            {mode === "forgot" && (
              <motion.div key="forgot" initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} exit={{ opacity: 0, scale: 0.95 }} className="flex flex-col gap-4">
                <p className="text-xs text-gray-400 text-center mb-2">Enter your email to receive a password reset code.</p>
                
                <div className="relative flex items-center">
                  <Mail className="absolute left-4 text-gray-500" size={18} />
                  <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Email address" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>
                
                <button type="submit" disabled={isLoading} className="mt-2 flex w-full items-center justify-center rounded-xl bg-qsr-red px-4 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70">
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : "Send Reset Code"}
                </button>
                <div className="mt-4 flex justify-center text-xs">
                  <button type="button" onClick={() => setMode("signin")} className="flex items-center gap-1 text-gray-400 hover:text-white"><ArrowLeft size={14}/> Back to Sign In</button>
                </div>
              </motion.div>
            )}

            {/* RESET PASSWORD MODE */}
            {mode === "reset" && (
              <motion.div key="reset" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -20 }} className="flex flex-col gap-4">
                <div className="relative flex items-center">
                  <Mail className="absolute left-4 text-gray-500" size={18} />
                  <input type="email" name="email" value={formData.email} onChange={handleChange} placeholder="Email address" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>
                
                <div className="relative flex items-center">
                  <KeyRound className="absolute left-4 text-gray-500" size={18} />
                  <input type="text" name="verificationCode" value={formData.verificationCode} onChange={handleChange} placeholder="Reset code from email" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-4 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                </div>

                <div className="relative flex items-center">
                  <Lock className="absolute left-4 text-gray-500" size={18} />
                  <input type={showPassword ? "text" : "password"} name="password" value={formData.password} onChange={handleChange} onFocus={() => setIsPasswordFocused(true)} onBlur={() => setIsPasswordFocused(false)} placeholder="New Password" required className="w-full rounded-xl border border-white/10 bg-black/50 py-3.5 pl-11 pr-12 text-sm text-white placeholder-gray-500 outline-none focus:border-qsr-red focus:bg-black/80" />
                  <button type="button" onClick={() => setShowPassword(!showPassword)} className="absolute right-4 text-gray-400 hover:text-white transition-colors focus:outline-none">
                    {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                  </button>
                </div>

                <AnimatePresence>
                  {isPasswordFocused && (
                    <motion.div
                      initial={{ opacity: 0, height: 0, marginTop: 0 }}
                      animate={{ opacity: 1, height: "auto", marginTop: 8 }}
                      exit={{ opacity: 0, height: 0, marginTop: 0 }}
                      className="overflow-hidden rounded-xl border border-white/10 bg-black/40 p-4"
                    >
                      <p className="mb-2 text-xs font-semibold text-gray-300">Password Requirements:</p>
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <ValidationItem label="8+ characters" isValid={passwordValidation.length} />
                        <ValidationItem label="Uppercase letter" isValid={passwordValidation.uppercase} />
                        <ValidationItem label="Lowercase letter" isValid={passwordValidation.lowercase} />
                        <ValidationItem label="Number" isValid={passwordValidation.number} />
                        <ValidationItem label="Special character" isValid={passwordValidation.symbol} />
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
                
                <button type="submit" disabled={isLoading} className="mt-2 flex w-full items-center justify-center rounded-xl bg-qsr-red px-4 py-3.5 text-sm font-semibold text-white shadow-lg transition-transform active:scale-[0.98] disabled:opacity-70">
                  {isLoading ? <Loader2 className="animate-spin" size={18} /> : "Reset Password"}
                </button>
                <div className="mt-4 flex justify-center text-xs">
                  <button type="button" onClick={() => setMode("signin")} className="flex items-center gap-1 text-gray-400 hover:text-white"><ArrowLeft size={14}/> Back to Sign In</button>
                </div>
              </motion.div>
            )}

          </AnimatePresence>
        </form>
      </motion.div>
    </div>
  );
}
