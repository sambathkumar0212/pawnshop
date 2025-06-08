/**
 * Camera Capture Utility for Customer Forms
 * This script handles the camera capture functionality for ID and profile images
 */

document.addEventListener('DOMContentLoaded', function() {
    // Check if we're on a page with camera capture functionality
    const cameraContainer = document.getElementById('camera-container');
    if (!cameraContainer) return;
    
    // Get references to camera elements
    const cameraButton = document.getElementById('capture-id-button');
    const cameraVideo = document.getElementById('camera-video');
    const captureButton = document.getElementById('take-picture-button');
    const retakeButton = document.getElementById('retake-picture-button');
    const confirmButton = document.getElementById('confirm-picture-button');
    const cancelButton = document.getElementById('cancel-picture-button');
    const cameraImageDataField = document.querySelector('input[name="camera_image_data"]');
    const idImagePreview = document.getElementById('id-image-preview');
    
    // Variables to track state
    let stream = null;
    
    // Function to open the camera
    function openCamera() {
        // Show the camera container
        cameraContainer.style.display = 'block';
        
        // Request camera access
        navigator.mediaDevices.getUserMedia({
            video: {
                width: { ideal: 1280 },
                height: { ideal: 720 },
                facingMode: 'environment' // Use back camera if available
            },
            audio: false
        })
        .then(function(mediaStream) {
            stream = mediaStream;
            cameraVideo.srcObject = stream;
            cameraVideo.play();
            
            // Show/hide appropriate buttons
            if (captureButton) captureButton.style.display = 'block';
            if (retakeButton) retakeButton.style.display = 'none';
            if (confirmButton) confirmButton.style.display = 'none';
            
            console.log('Camera opened successfully');
        })
        .catch(function(err) {
            console.error('Error accessing camera:', err);
            alert('Unable to access the camera: ' + err.message);
        });
    }
    
    // Function to close the camera
    function closeCamera() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
            stream = null;
        }
        
        cameraContainer.style.display = 'none';
        console.log('Camera closed');
    }
    
    // Function to capture an image from the video stream
    function captureImage() {
        if (!stream) return;
        
        // Create a canvas to capture the image
        const canvas = document.createElement('canvas');
        canvas.width = cameraVideo.videoWidth;
        canvas.height = cameraVideo.videoHeight;
        
        // Draw the current video frame to the canvas
        const ctx = canvas.getContext('2d');
        ctx.drawImage(cameraVideo, 0, 0, canvas.width, canvas.height);
        
        // Get the image data URL
        const imageDataUrl = canvas.toDataURL('image/jpeg', 0.9);
        
        // Show the captured image in the preview
        if (idImagePreview) {
            idImagePreview.src = imageDataUrl;
            idImagePreview.style.display = 'block';
        }
        
        // Update UI
        if (captureButton) captureButton.style.display = 'none';
        if (retakeButton) retakeButton.style.display = 'block';
        if (confirmButton) confirmButton.style.display = 'block';
        
        // Store the image data in the hidden field
        if (cameraImageDataField) {
            cameraImageDataField.value = imageDataUrl;
            console.log('Image data stored in form field');
        } else {
            console.error('Camera image data field not found!');
        }
    }
    
    // Set up event listeners
    if (cameraButton) {
        cameraButton.addEventListener('click', function(e) {
            e.preventDefault();
            openCamera();
        });
    }
    
    if (captureButton) {
        captureButton.addEventListener('click', function(e) {
            e.preventDefault();
            captureImage();
        });
    }
    
    if (retakeButton) {
        retakeButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Clear the stored image
            if (cameraImageDataField) cameraImageDataField.value = '';
            if (idImagePreview) idImagePreview.style.display = 'none';
            
            // Show capture button again
            if (captureButton) captureButton.style.display = 'block';
            if (retakeButton) retakeButton.style.display = 'none';
            if (confirmButton) confirmButton.style.display = 'none';
        });
    }
    
    if (confirmButton) {
        confirmButton.addEventListener('click', function(e) {
            e.preventDefault();
            closeCamera();
        });
    }
    
    if (cancelButton) {
        cancelButton.addEventListener('click', function(e) {
            e.preventDefault();
            // Clear any captured image
            if (cameraImageDataField) cameraImageDataField.value = '';
            if (idImagePreview) idImagePreview.style.display = 'none';
            closeCamera();
        });
    }
    
    // Cleanup when leaving the page
    window.addEventListener('beforeunload', function() {
        if (stream) {
            stream.getTracks().forEach(track => track.stop());
        }
    });
    
    console.log('Camera capture script loaded');
});
