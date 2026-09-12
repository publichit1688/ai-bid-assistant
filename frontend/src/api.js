import axios from "axios";


export const API_BASE_URL = (
    import.meta.env.VITE_API_BASE_URL
    || (import.meta.env.PROD ? window.location.origin : "http://127.0.0.1:8000")
).replace(/\/$/, "");

let accessToken = "";


export function setAccessToken(value){
    accessToken = String(value || "").trim();
}


export function clearAccessToken(){
    accessToken = "";
}


export function hasAccessToken(){
    return accessToken.length > 0;
}


export function toApiPath(value){
    const candidate = String(value || "");
    if(!candidate){
        return candidate;
    }
    if(candidate.startsWith(API_BASE_URL)){
        return candidate.slice(API_BASE_URL.length) || "/";
    }
    return candidate;
}


export const apiClient = axios.create({
    baseURL: API_BASE_URL,
    timeout: 120000
});


apiClient.interceptors.request.use((config)=>{
    if(accessToken){
        config.headers.Authorization = `Bearer ${accessToken}`;
    }
    return config;
});


apiClient.interceptors.response.use(
    (response)=>response,
    (error)=>{
        if(error.response?.status === 401 && typeof window !== "undefined"){
            window.dispatchEvent(new Event("app-auth-required"));
        }
        return Promise.reject(error);
    }
);
