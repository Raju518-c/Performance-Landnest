



// App.js or a top-level component
import React, { useEffect } from "react";
import api from "./api";  // axios instance with X-Session-Token header

function App() {
  useEffect(() => {
    const token = localStorage.getItem("session_token");

    if (token) {
      api.get("/auth/validate-session/")
        .then(res => {
          console.log("Session valid:", res.data);
        })
        .catch(err => {
          if (err.response && err.response.status === 401) {
            alert("Your session expired or logged in from another device.");
            localStorage.removeItem("session_token");
            window.location.href = "/login";
          }
        });
    }
  }, []);

  return (
    <div>
      {/* Your routes/components */}
    </div>
  );
}

export default App;





import React, { useState } from "react";
import axios from "axios";

function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showConfirm, setShowConfirm] = useState(false);

  const handleLogin = async () => {
    try {
      const res = await axios.post("/api/login/", { email, password });
      localStorage.setItem("token", res.data.token);
      alert("Login successful!");
    } catch (err) {
      if (err.response && err.response.status === 409) {
        // User already logged in somewhere else
        setShowConfirm(true);
      } else {
        alert("Login failed!");
      }
    }
  };

  const forceLogin = async () => {
    try {
      const res = await axios.post("/api/force-login/", { email });
      localStorage.setItem("token", res.data.token);
      setShowConfirm(false);
      alert("Forced login successful! Other device logged out.");
    } catch {
      alert("Force login failed!");
    }
  };

  return (
    <div>
      <h2>Login</h2>
      <input type="email" placeholder="Email" value={email}
        onChange={(e) => setEmail(e.target.value)} />
      <input type="password" placeholder="Password" value={password}
        onChange={(e) => setPassword(e.target.value)} />
      <button onClick={handleLogin}>Login</button>

      {showConfirm && (
        <div className="modal">
          <p>You are already logged in on another device.</p>
          <p>Do you want to logout from that device and continue?</p>
          <button onClick={forceLogin}>Yes, continue</button>
          <button onClick={() => setShowConfirm(false)}>Cancel</button>
        </div>
      )}
    </div>
  );
}

export default Login;
