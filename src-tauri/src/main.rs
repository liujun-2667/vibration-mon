#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::process::{Command, Child};
use std::sync::Mutex;
use tauri::Manager;
use serde::{Deserialize, Serialize};

struct AppState {
    python_process: Mutex<Option<Child>>,
}

#[derive(Serialize, Deserialize)]
struct ApiResponse<T> {
    success: bool,
    data: Option<T>,
    error: Option<String>,
}

#[tauri::command]
async fn proxy_request(
    path: String,
    method: String,
    body: Option<serde_json::Value>,
) -> Result<serde_json::Value, String> {
    let client = reqwest::Client::new();
    let url = format!("http://localhost:8000{}", path);
    
    let request = match method.as_str() {
        "GET" => client.get(&url),
        "POST" => client.post(&url).json(&body.unwrap_or(serde_json::json!({}))),
        "PUT" => client.put(&url).json(&body.unwrap_or(serde_json::json!({}))),
        "DELETE" => client.delete(&url),
        _ => return Err(format!("Unsupported method: {}", method)),
    };
    
    let response = request.send().await.map_err(|e| e.to_string())?;
    let json = response.json::<serde_json::Value>().await.map_err(|e| e.to_string())?;
    Ok(json)
}

#[tauri::command]
fn start_python_backend(state: tauri::State<AppState>) -> Result<String, String> {
    let mut process_guard = state.python_process.lock().unwrap();
    
    if process_guard.is_some() {
        return Ok("Python backend already running".to_string());
    }
    
    let python_exe = if cfg!(debug_assertions) {
        "python".to_string()
    } else {
        "./python/sidecar/python.exe".to_string()
    };
    
    let script_path = if cfg!(debug_assertions) {
        "./python/main.py".to_string()
    } else {
        "./python/main.py".to_string()
    };
    
    let child = Command::new(python_exe)
        .arg(&script_path)
        .spawn()
        .map_err(|e| format!("Failed to start Python backend: {}", e))?;
    
    *process_guard = Some(child);
    Ok("Python backend started successfully".to_string())
}

#[tauri::command]
fn stop_python_backend(state: tauri::State<AppState>) -> Result<String, String> {
    let mut process_guard = state.python_process.lock().unwrap();
    
    if let Some(mut child) = process_guard.take() {
        child.kill().map_err(|e| format!("Failed to kill Python backend: {}", e))?;
        Ok("Python backend stopped successfully".to_string())
    } else {
        Ok("Python backend was not running".to_string())
    }
}

fn main() {
    tauri::Builder::default()
        .manage(AppState {
            python_process: Mutex::new(None),
        })
        .invoke_handler(tauri::generate_handler![
            proxy_request,
            start_python_backend,
            stop_python_backend
        ])
        .setup(|app| {
            let app_handle = app.handle();
            tauri::async_runtime::spawn(async move {
                let state = app_handle.state::<AppState>();
                let _ = start_python_backend(state);
            });
            Ok(())
        })
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
