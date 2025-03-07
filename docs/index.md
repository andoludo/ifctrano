# 
<div style="display: flex; align-items: center;">
  <img src="img/ifctrano.webp" alt="Image" style="width: 120px; height: 140px; margin-right: 10px;">
  <span style="color: #FFBF00; font-size: 96px; font-weight: bold;">ifctrano</span>
</div>


## Overview
ifctrano is yet another **IFC to energy simulation** tool designed to translate **Industry Foundation Classes (IFC)** models into energy simulation models in **Modelica**.

### Key Differentiator
Unlike most translation approaches that rely on **space boundaries (IfcRelSpaceBoundary)**, ifctrano operates **solely on geometrical representation**. This is crucial because **space boundaries are rarely available** in IFC models. Instead, ifctrano requires at least the definition of **IfcSpace** objects to build energy simulation models.

### Space-Zone Mapping
For now, **each space is considered as a single thermal zone**, and the necessary space boundaries are **automatically generated**.

## Why ifctrano?
✅ No reliance on **IfcRelSpaceBoundary**

✅ Works with **geometric representation** only

✅ Supports **Modelica-based energy simulation**

✅ **Tested on multiple open-source IFC files**

## Research & Background
ifctrano is inspired by existing research, including **this journal paper**: [Automated Translation of IFC to Energy Models](https://www.sciencedirect.com/science/article/abs/pii/S0926580517308282). However, it takes a more **robust** and **practical** approach that doesn’t require explicit space boundaries.

## Open Source IFC Test Files
ifctrano has been tested using open-source IFC files from various repositories:

- 🐋 [BIM Whale IFC Samples](https://github.com/andrewisen/bim-whale-ifc-samples)
- 🏗️ [IfcSampleFiles](https://github.com/youshengCode/IfcSampleFiles)
- 🎭 [BIM2Modelica](https://github.com/UdK-VPT/BIM2Modelica/tree/master/IFC/IFC2X3/UdKB_Unit_Test_Cases)
- 🕸️ [Ifc2Graph Test Files](https://github.com/JBjoernskov/Ifc2Graph/tree/main/test_ifc_files)
- 🔓 [Open Source BIM](https://github.com/opensourceBIM)

## Installation & Usage
(Installation and usage instructions will be provided here, depending on the package distribution method.)



---
💡 **ifctrano** aims to make energy simulation model generation from IFC files **simpler, more accessible, and less reliant on incomplete IFC attributes**. 🚀
           

