import { useState, useRef, useEffect } from "react";

import TextareaAutosize from "./textareaAutosize.js";
import ChoicesSection from "./choice.js";

import styles from "./index.module.css";

const Input = ({
  showChoices,
  allowCustomInput = false,
  inputPlaceholder,
  explanationText,
  handleSend,
  choice,
  setChoice,
  setSelectedButton,
  options,
  setOptions,
}) => {
  const [selectedOption, setSelectedOption] = useState(null);
  const [showChoicesSection, setShowChoicesSection] = useState(false);

  useEffect(() => {
    setShowChoicesSection(showChoices);
  }, [showChoices]);

  const divRef = useRef(null);

  const handleMessageChange = (e) => {
    allowCustomInput && setChoice(e.target.value);
  };

  const handleButtonClick = (index, message) => {
    setSelectedButton(index);
    setChoice(message);

    if (selectedOption === null) {
      setSelectedOption([index, message]);
      let optionsCopy = options;
      delete optionsCopy[index];
      setOptions(optionsCopy);
    } else {
      let optionsCopy = options;
      delete optionsCopy[index];
      setSelectedOption([index, message]);
      options[selectedOption[0]] = selectedOption[1];
      setOptions(optionsCopy);
    }
  };

  return (
    <div
      ref={divRef}
      className={styles.wrapper}
      style={{
        borderRadius:
          showChoicesSection && Object.keys(options).length > 0
            ? "18px 18px 0 0"
            : 0,
      }}
    >
      {showChoicesSection && Object.keys(options).length > 0 && (
        <ChoicesSection
          explanationText={explanationText}
          options={options}
          handleButtonClick={handleButtonClick}
        />
      )}
      <div className={styles.inputWrapper}>
        <div className={styles.inputBubble}>
          <TextareaAutosize
            value={choice}
            onChange={handleMessageChange}
            placeholder={inputPlaceholder}
          />
        </div>
        <div
          className={styles.sendButton}
          style={{
            backgroundColor: choice.length === 0 ? "#3C3C43" : "#FFB930",
            color: choice.length === 0 ? "#ACACAC" : "#282828",
            cursor: choice.length === 0 ? "default" : "pointer",
          }}
          onClick={async () => {
            if (choice !== "") {
              let isAnyOptions = false;
              console.log(choice);

              if (options && Object.keys(options).length > 0) {
                console.log(1, typeof options, options);
                if (typeof options === "string") {
                  isAnyOptions = options === choice;
                  console.log(options === choice);
                } else {
                  isAnyOptions = Object.values(options).includes(choice);
                  console.log(
                    Object.values(options).includes(choice),
                    Object.values(options)
                  );
                }
              }

              if (selectedOption && Object.values(selectedOption).length > 0) {
                console.log("2", typeof selectedOption, selectedOption);

                if (typeof selectedOption === "string") {
                  isAnyOptions =
                    isAnyOptions && selectedOption === choice;

                  console.log(isAnyOptions, selectedOption === choice);
                } else {
                  isAnyOptions =
                    isAnyOptions ||
                    Object.values(selectedOption).includes(choice);

                  console.log(
                    isAnyOptions,
                    Object.values(selectedOption).includes(choice)
                  );
                }
              }

              console.log(!isAnyOptions, choice);

              handleSend(
                setShowChoicesSection,
                setSelectedOption,
                setOptions,
                !isAnyOptions
              );
            }
          }}
        >
          Send
        </div>
      </div>
    </div>
  );
};

export default Input;
