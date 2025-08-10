class PolaroidStudioPro {
  constructor() {
    this.backendUrl = window.location.origin
    this.currentImage = null
    this.currentImageBlob = null
    this.selectedFrame = "curvy"
    this.filters = {
      brightness: 100,
      contrast: 100,
      saturation: 100,
      tint: 50,
    }
    this.gallery = this.loadGallery()

    this.init()
  }

  init() {
    this.bindEvents()
    this.loadTheme()
    this.updateGallery()
    this.setupMobileOptimizations()
  }

  setupMobileOptimizations() {
    // Add touch event handling for better mobile experience
    if ("ontouchstart" in window) {
      document.body.classList.add("touch-device")
    }

    // Handle viewport changes for mobile
    const handleViewportChange = () => {
      const vh = window.innerHeight * 0.01
      document.documentElement.style.setProperty("--vh", `${vh}px`)
    }

    window.addEventListener("resize", handleViewportChange)
    handleViewportChange()

    // Prevent zoom on double tap for iOS
    let lastTouchEnd = 0
    document.addEventListener(
      "touchend",
      (event) => {
        const now = new Date().getTime()
        if (now - lastTouchEnd <= 300) {
          event.preventDefault()
        }
        lastTouchEnd = now
      },
      false,
    )
  }

  bindEvents() {
    // Theme toggle
    document.getElementById("themeToggle").addEventListener("click", () => this.toggleTheme())

    // Gallery
    document.getElementById("galleryBtn").addEventListener("click", () => this.showGallery())
    document.getElementById("closeGalleryBtn").addEventListener("click", () => this.showHome())

    // Upload
    const uploadArea = document.getElementById("uploadArea")
    const fileInput = document.getElementById("fileInput")

    uploadArea.addEventListener("click", () => fileInput.click())
    uploadArea.addEventListener("dragover", (e) => this.handleDragOver(e))
    uploadArea.addEventListener("dragleave", (e) => this.handleDragLeave(e))
    uploadArea.addEventListener("drop", (e) => this.handleDrop(e))
    fileInput.addEventListener("change", (e) => this.handleFileSelect(e.target.files[0]))

    // Editor
    document.getElementById("backBtn").addEventListener("click", () => this.showHome())
    document.getElementById("generateBtn").addEventListener("click", () => this.generatePolaroid())

    // Frame selection
    document.querySelectorAll(".frame-option").forEach((option) => {
      option.addEventListener("click", () => this.selectFrame(option.dataset.frame))
    })

    // Filters with value display
    this.bindFilterSlider("brightnessSlider", "brightnessValue", "brightness", "%")
    this.bindFilterSlider("contrastSlider", "contrastValue", "contrast", "%")
    this.bindFilterSlider("saturationSlider", "saturationValue", "saturation", "%")
    this.bindFilterSlider("tintSlider", "tintValue", "tint", "%")

    // Result actions
    document.getElementById("editAgainBtn").addEventListener("click", () => this.showEditor())
    document.getElementById("downloadBtn").addEventListener("click", () => this.downloadImage())
    document.getElementById("saveToGalleryBtn").addEventListener("click", () => this.saveToGallery())
    document.getElementById("createNewBtn").addEventListener("click", () => this.showHome())
  }

  bindFilterSlider(sliderId, valueId, filterKey, unit) {
    const slider = document.getElementById(sliderId)
    const valueDisplay = document.getElementById(valueId)

    slider.addEventListener("input", (e) => {
      const value = Number.parseInt(e.target.value)
      this.filters[filterKey] = value
      valueDisplay.textContent = value + unit
      this.applyFilters()
    })
  }

  // Theme Management
  toggleTheme() {
    const currentTheme = document.documentElement.getAttribute("data-theme")
    const newTheme = currentTheme === "dark" ? "light" : "dark"

    document.documentElement.setAttribute("data-theme", newTheme)
    localStorage.setItem("theme", newTheme)

    const icon = document.querySelector("#themeToggle i")
    icon.className = newTheme === "dark" ? "fas fa-sun" : "fas fa-moon"
  }

  loadTheme() {
    const savedTheme = localStorage.getItem("theme") || "light"
    document.documentElement.setAttribute("data-theme", savedTheme)

    const icon = document.querySelector("#themeToggle i")
    icon.className = savedTheme === "dark" ? "fas fa-sun" : "fas fa-moon"
  }

  // Screen Management
  showScreen(screenId) {
    document.querySelectorAll(".screen").forEach((screen) => {
      screen.classList.remove("active")
    })
    document.getElementById(screenId).classList.add("active")
  }

  showHome() {
    this.showScreen("homeScreen")
    this.resetEditor()
  }

  showEditor() {
    this.showScreen("editorScreen")
    if (this.currentImage) {
      document.getElementById("previewImage").src = this.currentImage
      this.applyFilters()
    }
  }

  showLoading() {
    this.showScreen("loadingScreen")
    this.animateLoadingSteps()
  }

  showResult() {
    this.showScreen("resultScreen")
  }

  showGallery() {
    this.showScreen("galleryScreen")
    this.updateGallery()
  }

  // File Handling
  handleFileSelect(file) {
    if (!file || !file.type.startsWith("image/")) {
      this.showToast("Please select a valid image file", "error")
      return
    }

    if (file.size > 10 * 1024 * 1024) {
      this.showToast("File size should be less than 10MB", "error")
      return
    }

    const reader = new FileReader()
    reader.onload = (e) => {
      this.currentImage = e.target.result
      this.showEditor()
      this.showToast("Image loaded successfully!", "success")
    }
    reader.readAsDataURL(file)
  }

  handleDragOver(e) {
    e.preventDefault()
    document.getElementById("uploadArea").classList.add("dragover")
  }

  handleDragLeave(e) {
    e.preventDefault()
    document.getElementById("uploadArea").classList.remove("dragover")
  }

  handleDrop(e) {
    e.preventDefault()
    document.getElementById("uploadArea").classList.remove("dragover")

    const files = e.dataTransfer.files
    if (files.length > 0) {
      this.handleFileSelect(files[0])
    }
  }

  // Editor Functionality
  selectFrame(frameType) {
    this.selectedFrame = frameType
    document.querySelectorAll(".frame-option").forEach((option) => {
      option.classList.toggle("active", option.dataset.frame === frameType)
    })

    // Update preview to match selected frame
    const previewImage = document.getElementById("previewImage")
    const previewContainer = document.querySelector(".preview-container")

    if (previewImage) {
      if (frameType === "curvy") {
        previewImage.style.borderRadius = "45px"
        if (previewContainer) {
          previewContainer.style.borderRadius = "45px"
        }
      } else {
        previewImage.style.borderRadius = "4px"
        if (previewContainer) {
          previewContainer.style.borderRadius = "8px"
        }
      }
    }

    this.showToast(`${frameType === "curvy" ? "Curvy Premium" : "Classic Sharp"} frame selected`, "success")
  }

  applyFilters() {
    const previewImage = document.getElementById("previewImage")
    if (!previewImage) return

    const { brightness, contrast, saturation, tint } = this.filters

    let filter = `brightness(${brightness}%) contrast(${contrast}%) saturate(${saturation}%)`

    // Apply tint effect (magenta/green balance)
    if (tint !== 50) {
      const tintValue = (tint - 50) / 50 // -1 to 1
      if (tintValue > 0) {
        // Magenta tint
        filter += ` hue-rotate(${tintValue * 15}deg) saturate(${100 + tintValue * 10}%)`
      } else {
        // Green tint
        filter += ` hue-rotate(${tintValue * 30}deg) saturate(${100 + Math.abs(tintValue) * 5}%)`
      }
    }

    previewImage.style.filter = filter

    // Maintain the correct frame style after applying filters
    if (this.selectedFrame === "curvy") {
      previewImage.style.borderRadius = "45px"
    } else {
      previewImage.style.borderRadius = "4px"
    }
  }

  resetEditor() {
    this.currentImage = null
    this.selectedFrame = "curvy"
    this.filters = { brightness: 100, contrast: 100, saturation: 100, tint: 50 }

    // Reset UI elements
    document.querySelectorAll(".frame-option").forEach((option) => {
      option.classList.toggle("active", option.dataset.frame === "curvy")
    })

    // Reset sliders and values
    document.getElementById("brightnessSlider").value = 100
    document.getElementById("contrastSlider").value = 100
    document.getElementById("saturationSlider").value = 100
    document.getElementById("tintSlider").value = 50

    document.getElementById("brightnessValue").textContent = "100%"
    document.getElementById("contrastValue").textContent = "100%"
    document.getElementById("saturationValue").textContent = "100%"
    document.getElementById("tintValue").textContent = "50%"
  }

  // Polaroid Generation
  async generatePolaroid() {
    if (!this.currentImage) {
      this.showToast("No image selected", "error")
      return
    }

    this.showLoading()

    try {
      const response = await fetch(this.currentImage)
      const blob = await response.blob()

      const formData = new FormData()
      formData.append("image", blob)
      formData.append("frame_style", this.selectedFrame)
      formData.append("filters", JSON.stringify(this.filters))

      const result = await fetch(`${this.backendUrl}/generate-polaroid`, {
        method: "POST",
        body: formData,
      })

      if (!result.ok) {
        throw new Error(`HTTP error! status: ${result.status}`)
      }

      const resultBlob = await result.blob()
      const imageUrl = URL.createObjectURL(resultBlob)

      this.currentImageBlob = resultBlob
      document.getElementById("resultImage").src = imageUrl
      this.showResult()
      this.showToast("Polaroid created successfully! ✨", "success")
    } catch (error) {
      console.error("Error generating polaroid:", error)
      this.showToast("Failed to generate polaroid. Please check your connection.", "error")
      this.showEditor()
    }
  }

  animateLoadingSteps() {
    const steps = document.querySelectorAll(".step")
    steps.forEach((step) => step.classList.remove("active"))

    const delays = [0, 1500, 3000, 4500]
    delays.forEach((delay, index) => {
      setTimeout(() => {
        if (steps[index]) {
          steps[index].classList.add("active")
          if (index > 0 && steps[index - 1]) {
            steps[index - 1].classList.remove("active")
          }
        }
      }, delay)
    })
  }

  // Result Actions
  downloadImage() {
    if (!this.currentImageBlob) return

    const url = URL.createObjectURL(this.currentImageBlob)
    const a = document.createElement("a")
    a.href = url
    a.download = `polaroid-${this.selectedFrame}-${Date.now()}.png`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)

    this.showToast("Polaroid downloaded successfully! 📥", "success")
  }

  saveToGallery() {
    if (!this.currentImageBlob) return

    const reader = new FileReader()
    reader.onload = () => {
      const galleryItem = {
        id: Date.now(),
        image: reader.result,
        date: new Date().toLocaleDateString(),
        frame: this.selectedFrame,
      }

      this.gallery.unshift(galleryItem)
      localStorage.setItem("polaroidGallery", JSON.stringify(this.gallery))
      this.showToast("Saved to gallery! 💾", "success")
    }
    reader.readAsDataURL(this.currentImageBlob)
  }

  // Gallery Management
  loadGallery() {
    try {
      return JSON.parse(localStorage.getItem("polaroidGallery") || "[]")
    } catch {
      return []
    }
  }

  updateGallery() {
    const galleryGrid = document.getElementById("galleryGrid")

    if (this.gallery.length === 0) {
      galleryGrid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 4rem; color: var(--text-tertiary);">
          <div style="font-size: 4rem; margin-bottom: 1rem; opacity: 0.5;">📸</div>
          <h3 style="font-size: 1.5rem; margin-bottom: 0.5rem; color: var(--text-secondary);">No polaroids yet</h3>
          <p>Create your first premium polaroid to see it here!</p>
        </div>
      `
      return
    }

    galleryGrid.innerHTML = this.gallery
      .map(
        (item) => `
      <div class="gallery-item" onclick="app.viewGalleryItem(${item.id})">
        <img src="${item.image}" alt="Polaroid">
        <div class="gallery-item-info">
          <div class="gallery-item-date">${item.date}</div>
          <div class="gallery-item-frame">${item.frame === "curvy" ? "Curvy Premium" : "Classic Sharp"}</div>
        </div>
      </div>
    `,
      )
      .join("")
  }

  viewGalleryItem(id) {
    const item = this.gallery.find((item) => item.id === id)
    if (item) {
      document.getElementById("resultImage").src = item.image
      this.showResult()
      this.currentImageBlob = null
    }
  }

  // Toast Notifications
  showToast(message, type = "info") {
    const toast = document.createElement("div")
    toast.className = `toast ${type}`

    const icon = type === "success" ? "✅" : type === "error" ? "❌" : "ℹ️"
    toast.innerHTML = `
      <span style="font-size: 1.2rem;">${icon}</span>
      <span>${message}</span>
    `

    const container = document.getElementById("toastContainer")
    container.appendChild(toast)

    setTimeout(() => toast.classList.add("show"), 100)

    setTimeout(() => {
      toast.classList.remove("show")
      setTimeout(() => {
        if (container.contains(toast)) {
          container.removeChild(toast)
        }
      }, 300)
    }, 4000)
  }
}

// Initialize app
let app
document.addEventListener("DOMContentLoaded", () => {
  app = new PolaroidStudioPro()
})

