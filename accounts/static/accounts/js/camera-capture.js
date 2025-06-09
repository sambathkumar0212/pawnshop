/**
 * Simple Camera Capture Utility for Customer Forms
 * Version 2.0 - Complete rewrite for better reliability
 */

document.addEventListener('DOMContentLoaded', function() {
    console.log('Camera capture script v2 initialized');
    
    // Core elements
    const captureButton = document.getElementById('capture-id-button');
    const cameraContainer = document.getElementById('camera-container');
    const cameraVideo = document.getElementById('camera-video');
    const takePictureButton = document.getElementById('take-picture-button');
    const retakePictureButton = document.getElementById('retake-picture-button');
    const confirmPictureButton = document.getElementById('confirm-picture-button');
    const cancelPictureButton = document.getElementById('cancel-picture-button');
    const idImagePreview = document.getElementById('id-image-preview');
    const hiddenImageField = document.getElementById('camera_image_data');
    
    // Exit if not on a page with camera functionality
    if (!captureButton || !cameraContainer) {
        console.log('Camera capture elements not found on this page');
        return;
    }
    
    console.log('Camera capture elements found, setting up event handlers');
    
    // Global variables
    let mediaStream = null;
    
    // Initialize camera UI
    function setupCamera() {
        // Button to open camera
        captureButton.addEventListener('click', function(e) {
            e.preventDefault();
            openCamera();
        });
        
        // Take picture button
        takePictureButton.addEventListener('click', function(e) {
            e.preventDefault();
            takePicture();
        });
        
        // Retake picture button
        retakePictureButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Reset UI for taking another picture
            takePictureButton.style.display = 'inline-block';
            retakePictureButton.style.display = 'none';
            confirmPictureButton.style.display = 'none';
            // Clear any previous image
            if (idImagePreview) {
                idImagePreview.style.display = 'none';
            }
        });
        
        // Confirm picture button
        confirmPictureButton.addEventListener('click', function(e) {
            e.preventDefault();
            closeCamera();
        });
        
        // Cancel button
        cancelPictureButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Clear the preview and hidden field
            if (idImagePreview) {
                idImagePreview.style.display = 'none';
            }
            if (hiddenImageField) {
                hiddenImageField.value = '';
            }
            closeCamera();
        });
        
        console.log('Camera event handlers initialized');
    }
    
    // Open camera function
    function openCamera() {
        console.log('Attempting to open camera...');
        
        // Show camera container
        cameraContainer.style.display = 'block';
        
        // Reset UI state
        takePictureButton.style.display = 'inline-block';
        retakePictureButton.style.display = 'none';
        confirmPictureButton.style.display = 'none';
        
        // Request camera access with explicit error handling
        if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
            navigator.mediaDevices.getUserMedia({
                video: {
                    facingMode: 'environment', // Prefer back camera
                    width: { ideal: 1280 },
                    height: { ideal: 720 }
                },
                audio: false
            })
            .then(function(stream) {
                mediaStream = stream;
                
                // Connect stream to video element
                cameraVideo.srcObject = stream;
                cameraVideo.onloadedmetadata = function() {
                    cameraVideo.play()
                    .then(() => console.log('Camera started successfully'))
                    .catch(err => console.error('Error starting video:', err));
                };
                
                console.log('Camera access granted');
            })
            .catch(function(error) {
                console.error('Error accessing camera:', error);
                alert('Could not access camera: ' + error.message);
                cameraContainer.style.display = 'none';
            });
        } else {
            console.error('getUserMedia not supported in this browser');
            alert('Camera access is not supported in this browser. Please try a different browser.');
            cameraContainer.style.display = 'none';
        }
    }
    
    // Take picture function
    function takePicture() {
        console.log('Taking picture...');
        
        if (!mediaStream) {
            console.error('No active camera stream');
            return;
        }
        
        try {
            // Create canvas at video dimensions
            const canvas = document.createElement('canvas');
            canvas.width = cameraVideo.videoWidth;
            canvas.height = cameraVideo.videoHeight;
            
            // Draw current video frame to canvas
            const context = canvas.getContext('2d');
            context.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
            
            // Get image as data URL
            const imageDataUrl = canvas.toDataURL('image/jpeg', 0.85);
            
            // Update preview image
            idImagePreview.src = imageDataUrl;
            idImagePreview.style.display = 'block';
            
            // Store in hidden field
            hiddenImageField.value = imageDataUrl;
            
            // Update UI
            takePictureButton.style.display = 'none';
            retakePictureButton.style.display = 'inline-block';
            confirmPictureButton.style.display = 'inline-block';
            
            console.log('Picture taken successfully');
        } catch (error) {
            console.error('Error taking picture:', error);
            alert('Error taking picture: ' + error.message);
        }
    }
    
    // Close camera function
    function closeCamera() {
        console.log('Closing camera...');
        
        // Stop all tracks in the stream
        if (mediaStream) {
            mediaStream.getTracks().forEach(function(track) {
                track.stop();
            });
            mediaStream = null;
        }
        
        // Hide camera container
        cameraContainer.style.display = 'none';
        
        console.log('Camera closed');
    }
    
    // Cleanup on page unload
    window.addEventListener('beforeunload', function() {
        if (mediaStream) {
            mediaStream.getTracks().forEach(track => track.stop());
        }
    });
    
    // Initialize camera UI
    setupCamera();
    console.log('Camera capture script v2 initialized successfully');
});
