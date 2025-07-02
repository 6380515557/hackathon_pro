import React, { useState } from "react";
import "../styles/ProductionEntry.css";

const ProductionEntry = () => {
  const [formData, setFormData] = useState({
    date: "",
    machineId: "",
    shift: "",
    productName: "",
    quantity: "",
    remarks: "",
  });

  const handleChange = (e) => {
    setFormData({ ...formData, [e.target.name]: e.target.value });
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    console.log("Submitted Data:", formData);
    alert("Production data submitted successfully!");
  };

  return (
    <div className="entry-container">
      <div className="entry-card">
        <h2>Production Data Entry</h2>
        <form onSubmit={handleSubmit}>
          <div className="input-group">
            <label>Date</label>
            <input type="date" name="date" value={formData.date} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Machine ID</label>
            <input type="text" name="machineId" placeholder="Enter machine ID" value={formData.machineId} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Shift</label>
            <select name="shift" value={formData.shift} onChange={handleChange} required>
              <option value="">Select Shift</option>
              <option value="Morning">Morning</option>
              <option value="Evening">Evening</option>
              <option value="Night">Night</option>
            </select>
          </div>
          <div className="input-group">
            <label>Product Name/Type</label>
            <input type="text" name="productName" placeholder="Enter product name/type" value={formData.productName} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Quantity Produced</label>
            <input type="number" name="quantity" placeholder="Enter quantity" value={formData.quantity} onChange={handleChange} required />
          </div>
          <div className="input-group">
            <label>Comments / Remarks</label>
            <textarea name="remarks" rows="3" placeholder="Any additional comments" value={formData.remarks} onChange={handleChange}></textarea>
          </div>
          <button type="submit">Submit Entry</button>
        </form>
      </div>
    </div>
  );
};

export default ProductionEntry;
